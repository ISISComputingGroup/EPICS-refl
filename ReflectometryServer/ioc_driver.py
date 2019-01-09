"""
The driving layer communicates between the component layer and underlying pvs.
"""

import math
import logging

logger = logging.getLogger(__name__)

# Tolerance within which the position will be declared out of the beam. 1 mm tolerance.
TOLERANCE_ON_OUT_OF_BEAM_POSITION = 1


class IocDriver(object):
    """
    Drives an actual motor axis based on a component in the beamline model.
    """
    def __init__(self, component, axis):
        """
        Drive the IOC based on a component
        Args:
            component (ReflectometryServer.components.Component):
            axis (ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV that this driver controls.
        """
        self._component = component
        self._axis = axis
        self._axis.add_after_value_change_listener(self._trigger_after_axis_value_change_listener)

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
        return component == self._component

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

        self._axis.value = self._get_set_point_position()

    def _get_distance(self):
        """
        :return: The distance between the target component position and the actual motor position in y.
        """
        return math.fabs(self._axis.value - self._get_set_point_position())

    def _get_set_point_position(self):
        """

        Returns:

        """
        raise NotImplemented()

    def _trigger_after_axis_value_change_listener(self, new_value, alarm_severity, alarm_status):
        """
        Trigger all listeners after an axis value change.
        Args:
            new_value: new axis value that is given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """

        raise NotImplemented()


class DisplacementDriver(IocDriver):
    """
    Drives a component with linear displacement movement
    """
    def __init__(self, component, height_axis, out_of_beam_position=None):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): The component providing the values for the axes
            height_axis (ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV that this driver controls.
            out_of_beam_position (float): this position that the component should be in when out of the beam; None for
                can not set the component to be out of the beam
        """
        super(DisplacementDriver, self).__init__(component, height_axis)
        self._out_of_beam_position = out_of_beam_position

    def _trigger_after_axis_value_change_listener(self, new_value, alarm_severity, alarm_status):
        """
        Trigger all listeners after a height change.
        Args:
            new_value: new height that is given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """
        if self._out_of_beam_position is not None:
            distance_to_out_of_beam = abs(new_value - self._out_of_beam_position)
            self._component.beam_path_rbv.is_in_beam = distance_to_out_of_beam > TOLERANCE_ON_OUT_OF_BEAM_POSITION
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
            angle_axis(ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): PV for the angle motor axis
        """
        super(AngleDriver, self).__init__(component, angle_axis)

    def _trigger_after_axis_value_change_listener(self, new_value, alarm_severity, alarm_status):
        """
        Trigger all listeners after a angle change.
        Args:
            new_value: new angle given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """
        self._component.beam_path_rbv.angle = new_value

    def _get_set_point_position(self):
        return self._component.beam_path_set_point.angle
