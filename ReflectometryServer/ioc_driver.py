"""
The driving layer communicates between the component layer and underlying pvs.
"""

import math
import logging
from ReflectometryServer.components import ChangeAxis

logger = logging.getLogger(__name__)


class IocDriver(object):
    """
    Drives an actual motor axis based on a component in the beamline model.
    """
    def __init__(self, component, axis, synchronised=True):
        """
        Drive the IOC based on a component
        Args:
            component (ReflectometryServer.components.Component):
            axis (ReflectometryServer.pv_wrapper.MotorPVWrapper): The PV that this driver controls.
            synchronised (bool): If True then axes will set their velocities so they arrive at the end point at the same
                time; if false they will move at their current speed.
        """
        self._component = component
        self._axis = axis
        self._rbv_cache = self._axis.rbv
        self._sp_cache = None
        self._synchronised = synchronised

        self._axis.add_after_rbv_change_listener(self._on_update_rbv)
        self._axis.add_after_sp_change_listener(self._on_update_sp)

    def __repr__(self):
        return "{} for axis pv {} and component {}".format(
            self.__class__.__name__, self._axis.name, self._component.name)

    def initialise(self):
        """
        Post monitors and read initial value from the axis.
        """
        self._axis.initialise()
        self.initialise_setpoint()

    def initialise_setpoint(self):
        """
        Initialise the setpoint beam model in the component layer with an initial value read from the motor axis.
        """
        raise NotImplemented()

    def is_for_component(self, component):
        """
        Does this driver use the component given.
        Args:
            component: the component to check

        Returns: True if this ioc driver uses the component; false otherwise
        """
        return component is self._component

    def _axis_will_move(self):
        """
        Returns: True if the axis set point has changed and it will move any distance
        """
        return not self.at_target_setpoint() and self._is_changed()

    def _get_duration_parameters(self):
        """
        Returns: gets the parameters used for calculating duration
        direction, rbv, sp, bdst, mvel, bvel
        """
        return self._axis.direction, self.rbv_cache(), self._get_set_point_position(),\
               self._axis.backlash_distance, self._axis.max_velocity, self._axis.backlash_velocity

    def _backlash_duration(self, (direction, rbv, sp, bdst, vmax, bvel)):
        """
        Args:
            direction: the current dir setting of the motor
            rbv: the position read back value
            sp: the set point
            bdst: the backlash distance
            vmax: the maximum velocity (not used)
            bvel: the backlash velocity
        Returns: the duration of the backlash move
        """
        # If the speeds are zero on a motor which is going to move, error as it makes no sense
        # to move a non-zero distance with a zero velocity
        if vmax == 0 or vmax is None:
            raise ZeroDivisionError("Motor max velocity is zero or none")
        if (bvel == 0 or bvel is None) and not (bdst == 0 or bdst is None):
            raise ZeroDivisionError("Backlash speed is zero or none")

        if bvel == 0 or bvel is None:
            # Return 0 instead of error as when this is called by perform_move it can be on motors which are
            # not in fact moving, and may not have been set up yet
            return 0
        elif min([0, bdst]) <= rbv - sp <= max([0, bdst]):
            # If the motor is already within the backlash distance
            return math.fabs(rbv - sp) / bvel
        else:
            return math.fabs(bdst) / bvel

    def _base_move_duration(self, (direction, rbv, sp, bdst, vmax, bvel)):
        """
        Args:
            direction: the current dir setting of the motor
            rbv: the position read back value
            sp: the set point
            bdst: the backlash distance
            vmax: the maximum velocity (not used)
            bvel: the backlash velocity
        Returns: the duration move without the backlash
        """
        if not (min([0, bdst]) <= rbv - sp <= max([0, bdst])):
            # If the motor is not already within the backlash distance
            return math.fabs(rbv - (sp + bdst)) / vmax
        else:
            return 0

    def get_max_move_duration(self):
        """
        Returns: The maximum duration of the requested move for all associated axes. If axes are not synchronised this
        will return 0 but movement will still be required.
        """
        if self._axis_will_move() and self._synchronised:
            backlash_duration = self._backlash_duration(self._get_duration_parameters())
            base_move_duration = self._base_move_duration(self._get_duration_parameters())

            duration = base_move_duration + backlash_duration

            return duration
        else:
            return 0.0

    def perform_move(self, move_duration, force=False):
        """
        Tells the driver to perform a move to the component set points within a given duration

        Args:
            move_duration (float): The duration in which to perform this move
            force (bool): move even if component does not report changed
        """

        if self._axis_will_move() or force:
            move_duration -= self._backlash_duration(self._get_duration_parameters())
            logger.debug("Moving axis {} {}".format(self._axis.name, self._get_distance()))
            if move_duration > 1e-6 and self._synchronised:
                self._axis.initiate_move_with_change_of_velocity()
                self._axis.velocity = self._get_distance() / move_duration
            self._axis.sp = self._get_set_point_position()
            self._sp_cache = self._get_set_point_position()
        self._clear_changed()

    def _is_changed(self):
        """
        Returns whether this driver's component has been flagged for change.
        """
        raise NotImplemented("This should be implemented in the subclass")

    def _clear_changed(self):
        """
        Clears the flag indicating whether this driver's component has been changed.
        """
        raise NotImplemented("This should be implemented in the subclass")

    def rbv_cache(self):
        """
        Return the last cached readback value of the underlying motor if one exists; throws an exception otherwise.

        Returns: The cached readback value for the motor
        """
        if self._rbv_cache is None:
            raise ValueError("Axis {} not initialised. Check configuration is correct and motor IOC is running."
                             .format(self._axis.name))
        return self._rbv_cache

    def _get_distance(self):
        """
        :return: The distance between the target component position and the actual motor position in y.
        """
        bdst = self._axis.backlash_distance
        return math.fabs(self.rbv_cache() - (self._get_set_point_position() + bdst))

    def _get_set_point_position(self):
        """

        Returns:

        """
        raise NotImplemented()

    def _on_update_rbv(self, new_value, alarm_severity, alarm_status):
        """
        Listener to trigger on a change of the readback value of the underlying motor.

        Args:
            new_value: new axis readback value that is given
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._rbv_cache = new_value
        self._propagate_rbv_change(new_value, alarm_severity, alarm_status)

    def _propagate_rbv_change(self, new_value, alarm_severity, alarm_status):
        """
        Signal that the motor readback value has changed to the middle component layer. Subclass must implement this
        method.

        Args:
            new_value: new axis value that is given
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        raise NotImplemented()

    def _on_update_sp(self, value, alarm_severity, alarm_status):
        """
        Updates the cached set point for this axis with a new value.
        Args:
            value: The new set point value.
        """
        self._sp_cache = value

    def at_target_setpoint(self):
        """
        Returns: True if the setpoint on the component and the one on the motor PV are the same (within tolerance),
            False if they differ.
        """
        if self._sp_cache is None:
            return False

        difference = abs(self._get_set_point_position() - self._sp_cache)
        return difference < self._axis.resolution


class DisplacementDriver(IocDriver):
    """
    Drives a component with linear displacement movement
    """
    def __init__(self, component, motor_axis, out_of_beam_position=None, tolerance_on_out_of_beam_position=1,
                 synchronised=True):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): The component providing the values for the axes
            motor_axis (ReflectometryServer.pv_wrapper.MotorPVWrapper): The PV that this driver controls.
            out_of_beam_position (float): this position that the component should be in when out of the beam; None for
                can not set the component to be out of the beam
            tolerance_on_out_of_beam_position (float): this the tolerance on the out of beam position, if the motor
                is within this tolerance of the out_of_beam_position it will read out of beam otherwise the position
            synchronised (bool): If True then axes will set their velocities so they arrive at the end point at the same
                time; if false they will move at their current speed.
        """
        super(DisplacementDriver, self).__init__(component, motor_axis, synchronised)
        self._out_of_beam_position = out_of_beam_position
        self._tolerance_on_out_of_beam_position = tolerance_on_out_of_beam_position

    def _get_in_beam_status(self, value):
        if self._out_of_beam_position is not None:
            distance_to_out_of_beam = abs(value - self._out_of_beam_position)
            in_beam_status = distance_to_out_of_beam > self._tolerance_on_out_of_beam_position
        else:
            in_beam_status = True
        return in_beam_status

    def initialise_setpoint(self):
        """
        Initialise the setpoint beam model in the component layer with an initial value read from the motor axis.
        """
        sp = self._axis.sp
        if self._out_of_beam_position is not None:
            self._component.beam_path_set_point.is_in_beam = self._get_in_beam_status(sp)
        self._component.beam_path_set_point.init_displacement_from_motor(sp)

    def _propagate_rbv_change(self, new_value, alarm_severity, alarm_status):
        """
        Propagate the new height readback value to the middle component layer.

        Args:
            new_value: new height readback value that is given
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if self._out_of_beam_position is not None:
            self._component.beam_path_rbv.is_in_beam = self._get_in_beam_status(new_value)
        self._component.beam_path_rbv.set_displacement(new_value, alarm_severity, alarm_status)

    def _get_set_point_position(self):
        if self._component.beam_path_set_point.is_in_beam:
            displacement = self._component.beam_path_set_point.get_displacement()
        else:
            if self._out_of_beam_position is None:
                displacement = 0
                logger.error("The component, {},is out of the beam but there is no out of beam position for the driver "
                             "running axis{}".format(self._component.name, self._axis.name))
            else:
                displacement = self._out_of_beam_position
        return displacement

    def has_out_of_beam_position(self):
        """
        Returns: True if this Displacement driver has out of beam position set; False otherwise.
        """
        return self._out_of_beam_position is not None

    def _component_changed(self):
        return self._component.read_changed_flag(ChangeAxis.POSITION)

    def _is_changed(self):
        """
        Returns whether this driver's component's position has been flagged for change.
        """
        return self._component.read_changed_flag(ChangeAxis.POSITION)

    def _clear_changed(self):
        """
        Clears the flag indicating whether the this driver's component's position has been changed.
        """
        self._component.set_changed_flag(ChangeAxis.POSITION, False)


class AngleDriver(IocDriver):
    """
    Drives a component that has variable angle.
    """
    def __init__(self, component, angle_axis, synchronised=True):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): Component providing the values for the axes
            angle_axis(ReflectometryServer.pv_wrapper.MotorPVWrapper): PV for the angle motor axis
            synchronised (bool): If True then axes will set their velocities so they arrive at the end point at the same
                time; if false they will move at their current speed.
        """
        super(AngleDriver, self).__init__(component, angle_axis, synchronised)

    def initialise_setpoint(self):
        """
        Initialise the setpoint beam model in the component layer with an initial value read from the motor axis.
        """
        self._component.beam_path_set_point.init_angle_from_motor(self._axis.sp)

    def _propagate_rbv_change(self, new_value, alarm_severity, alarm_status):
        """
        Propagate the new angle readback value to the middle component layer.

        Args:
            new_value: new angle readback value that is given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """
        self._component.beam_path_rbv.angle = new_value

    def _get_set_point_position(self):
        return self._component.beam_path_set_point.angle

    def _is_changed(self):
        """
        Returns whether this driver's component angle has been flagged for change.
        """
        return self._component.read_changed_flag(ChangeAxis.ANGLE)

    def _clear_changed(self):
        """
        Clears the flag indicating whether the this driver's component's angle has been changed.
        """
        self._component.set_changed_flag(ChangeAxis.ANGLE, False)
