"""
The driving layer communicates between the component layer and underlying pvs.
"""

import math
import logging

logger = logging.getLogger(__name__)


class IocDriver(object):
    """
    Drives an actual motor axis based on a component in the beamline model.
    """
    def __init__(self, component, axis):
        """
        Drive the IOC based on a component
        Args:
            component (ReflectometryServer.components.Component):
            axis (ReflectometryServer.pv_wrapper.MotorPVWrapper): The PV that this driver controls.
        """
        self._component = component
        self._axis = axis
        self._rbv_cache = self._axis.rbv
        self._sp_cache = None
        self._axis.add_after_rbv_change_listener(self._rbv_change_listener)
        self._axis.add_after_sp_change_listener(self._update_sp_cache)

    def __repr__(self):
        return "{} for axis pv {} and component {}".format(
            self.__class__.__name__, self._axis.name, self._component.name)

    def is_for_component(self, component):
        """
        Does this driver use the component given.
        Args:
            component: the component to check

        Returns: True if this ioc driver uses the component; false otherwise
        """
        return component is self._component

    def get_max_move_duration(self):
        """
        Returns: The maximum duration of the requested move for all associated axes
        """
        return self._get_distance() / self._axis.max_velocity

    def perform_move(self, move_duration):
        """
        Tells the driver to perform a move to the component set points within a given duration

        Args:
            move_duration: The duration in which to perform this move
        """
        logger.debug("Moving axis {}".format(self._get_distance()))
        if move_duration > 1e-6:  # TODO Is this the correct thing to do and if so test it
            self._axis.velocity = self._get_distance() / move_duration

        self._axis.sp = self._get_set_point_position()
        self._sp_cache = self._get_set_point_position()

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
        return math.fabs(self.rbv_cache() - self._get_set_point_position())

    def _get_set_point_position(self):
        """

        Returns:

        """
        raise NotImplemented()

    def _rbv_change_listener(self, new_value, alarm_severity, alarm_status):
        """
        Listener to trigger on a change of the readback value of the underlying motor.

        Args:
            new_value: new axis value that is given
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

    def _update_sp_cache(self, value, alarm_severity, alarm_status):
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
    def __init__(self, component, motor_axis, out_of_beam_position=None, tolerance_on_out_of_beam_position=1):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): The component providing the values for the axes
            motor_axis (ReflectometryServer.pv_wrapper.MotorPVWrapper): The PV that this driver controls.
            out_of_beam_position (float): this position that the component should be in when out of the beam; None for
                can not set the component to be out of the beam
            tolerance_on_out_of_beam_position (float): this the tolerance on the out of beam position, if the motor
                is within this tolerance of the out_of_beam_position it will read out of beam otherwise the position
        """
        super(DisplacementDriver, self).__init__(component, motor_axis)
        self._out_of_beam_position = out_of_beam_position
        self._tolerance_on_out_of_beam_position = tolerance_on_out_of_beam_position

    def _propagate_rbv_change(self, new_value, alarm_severity, alarm_status):
        """
        Propagate the new height to the middle component layer.

        Args:
            new_value: new height that is given
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if self._out_of_beam_position is not None:
            distance_to_out_of_beam = abs(new_value - self._out_of_beam_position)
            self._component.beam_path_rbv.is_in_beam = distance_to_out_of_beam > self._tolerance_on_out_of_beam_position
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


class AngleDriver(IocDriver):
    """
    Drives a component that has variable angle.
    """
    def __init__(self, component, angle_axis):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): Component providing the values for the axes
            angle_axis(ReflectometryServer.pv_wrapper.MotorPVWrapper): PV for the angle motor axis
        """
        super(AngleDriver, self).__init__(component, angle_axis)

    def _propagate_rbv_change(self, new_value, alarm_severity, alarm_status):
        """
        Propagate the new angle to the middle component layer.

        Args:
            new_value: new angle given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """
        self._component.beam_path_rbv.angle = new_value

    def _get_set_point_position(self):
        return self._component.beam_path_set_point.angle
