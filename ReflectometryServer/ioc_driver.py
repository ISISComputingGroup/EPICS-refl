"""
The driving layer communicates between the component layer and underlying pvs.
"""

import math
import logging

logger = logging.getLogger(__name__)


class IocDriver(object):
    """
    Drives an actual motor IOC based on a component in the beamline model.
    """
    def __init__(self, component):
        """
        Drive the IOC based on a component
        Args:
            component (ReflectometryServer.components.Component):
        """
        self._component = component

    def get_max_move_duration(self):
        """
        This should be overridden in the subclass
        Returns: The maximum duration of the requested move for all associated axes
        """
        raise NotImplemented()

    def perform_move(self, move_duration):
        """
        This should be overridden in the subclass. Tells the driver to perform a move to the component set points within
        a given duration
        :param move_duration: The duration in which to perform this move
        """
        raise NotImplemented()


class HeightDriver(IocDriver):
    """
    Drives a component with vertical movement
    """
    def __init__(self, component, height_axis):
        """
        Constructor.
        Args:
            component (ReflectometryServer.components.Component): The component providing the values for the axes
            height_axis (ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV that this driver controls.
        """
        super(HeightDriver, self).__init__(component)
        self._height_axis = height_axis
        self._height_axis.add_after_value_change_listener(self._trigger_after_height_change_listeners)

    def _trigger_after_height_change_listeners(self, new_value, alarm_severity, alarm_status):
        """
        Trigger all listeners after a height change.
        Args:
            new_value: new height that is given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """

        self._component.beam_path_rbv.set_displacement(new_value, alarm_severity, alarm_status)

    def _get_distance_height(self):
        """
        :return: The distance between the target component position and the actual motor position in y.
        """
        return math.fabs(self._height_axis.value - self._component.beam_path_set_point.get_displacement())

    def get_max_move_duration(self):
        """
        :return: The expected duration of a move based on move distance and axis speed.
        """
        return self._get_distance_height() / self._height_axis.max_velocity

    def perform_move(self, move_duration):
        """
        Tells the height axis to move to the setpoint within a given time frame.
        :param move_duration: The desired duration of the move.
        """
        logger.debug("Moving axis {}".format(self._get_distance_height()))
        if move_duration > 1e-6:  # TODO Is this the correct thing to do and if so test it
            self._height_axis.velocity = self._get_distance_height() / move_duration

        self._height_axis.value = self._component.beam_path_set_point.get_displacement()


class HeightAndTiltDriver(HeightDriver):
    """
    Drives a component that has variable tilt in order to stay perpendicular to the beam in addition to variable height.
    """
    ANGULAR_OFFSET = 90.0

    def __init__(self, component, height_axis, tilt_axis):
        """
        Constructor.
        :param component (ReflectometryServer.components.TiltingJaws): The component providing the values for the axes
        :param height_axis (ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV for the height motor axis
        :param tilt_axis (ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV for the tilt motor axis
        """
        super(HeightAndTiltDriver, self).__init__(component, height_axis)
        self._tilt_axis = tilt_axis

    def _target_angle_perpendicular(self):
        return self._component.beam_path_set_point.calculate_tilt_angle() - self.ANGULAR_OFFSET

    def get_max_move_duration(self):
        """
        :return: The expected duration of a move based on move distance and axis speed for the slowest axis.
        """
        vertical_move_duration = self._get_distance_height() / self._height_axis.max_velocity
        distance_to_move = math.fabs(self._tilt_axis.value - self._target_angle_perpendicular())
        angular_move_duration = distance_to_move / self._tilt_axis.max_velocity
        return max(vertical_move_duration, angular_move_duration)

    def perform_move(self, move_duration):
        """
        Tells the height and tilt axes to move to the setpoint within a given time frame.
        :param move_duration: The desired duration of the move.
        """
        self._height_axis.velocity = self._get_distance_height() / move_duration
        self._tilt_axis.velocity = math.fabs(self._tilt_axis.value - self._target_angle_perpendicular()) / move_duration
        self._height_axis.value = self._component.beam_path_set_point.get_displacement()
        self._tilt_axis.value = self._component.beam_path_set_point.calculate_tilt_angle()


class HeightAndAngleDriver(HeightDriver):
    """
    Drives a component that has variable height and angle.
    """
    def __init__(self, component, height_axis, angle_axis):
        """
        Constructor.
        :param component (ReflectometryServer.components.ReflectingComponent):
            The component providing the values for the axes
        :param height_axis(ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV for the height motor axis
        :param angle_axis(ReflectometryServer.motor_pv_wrapper.MotorPVWrapper): The PV for the angle motor axis
        """
        super(HeightAndAngleDriver, self).__init__(component, height_axis)
        self._angle_axis = angle_axis
        self._angle_axis.add_after_value_change_listener(self._trigger_after_angle_change_listeners)

    def _trigger_after_angle_change_listeners(self, new_value, alarm_severity, alarm_status):
        """
        Trigger all listeners after a angle change.
        Args:
            new_value: new angle given
            alarm_severity (CaChannel._ca.AlarmSeverity): severity of any alarm
            alarm_status (CaChannel._ca.AlarmCondition): the alarm status
        """

        self._component.beam_path_rbv.angle = new_value

    def get_max_move_duration(self):
        """
        :return: The expected duration of a move based on move distance and axis speed for the slowest axis.
        """
        height_to_move = math.fabs(self._height_axis.value - self._component.beam_path_set_point.sp_position().y)
        vertical_move_duration = height_to_move / self._height_axis.max_velocity
        angle_to_move = math.fabs(self._angle_axis.value - self._component.beam_path_set_point.angle)
        angular_move_duration = angle_to_move / self._angle_axis.max_velocity
        return max(vertical_move_duration, angular_move_duration)

    def perform_move(self, move_duration):
        """
        Tells the height and angle axes to move to the setpoint within a given time frame.
        :param move_duration: The desired duration of the move.
        """
        height_to_move = math.fabs(self._height_axis.value - self._component.beam_path_set_point.get_displacement())
        self._height_axis.velocity = height_to_move / move_duration
        angle_to_move_through = self._angle_axis.value - self._component.beam_path_set_point.angle
        self._angle_axis.velocity = math.fabs(angle_to_move_through) / move_duration
        self._height_axis.value = self._component.beam_path_set_point.get_displacement()
        self._angle_axis.value = self._component.beam_path_set_point.angle
