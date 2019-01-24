"""
Objects to help with calculating the beam path when interacting with a component. This is used for instance for the
set points or readbacks etc.
"""
from math import degrees, atan2

from ReflectometryServer.geometry import PositionAndAngle
import logging

logger = logging.getLogger(__name__)


class TrackingBeamPathCalc(object):
    """
    Calculator for the beam path when it interacts with a component that can track the beam.
    """

    def __init__(self, movement_strategy):
        """
        Initialiser.
        Args:
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovementCalc): strategy for calculating the
                interception between the movement of the component and the beam.
        """
        self._incoming_beam = None
        self._after_beam_path_update_listeners = set()
        self._after_physical_move_listeners = set()
        self._is_in_beam = True
        self._movement_strategy = movement_strategy

    def add_after_beam_path_update_listener(self, listener):
        """
        Add a listener which is triggered if the beam path is changed. For example if displacement is set or incoming
        beam is changed.
        Args:
            listener: listener with a single argument which is the calling calculation.
        """
        self._after_beam_path_update_listeners.add(listener)

    def _trigger_after_beam_path_update(self):
        """
        Runs all the current listeners because something about the beam path has changed.
        """
        for listener in self._after_beam_path_update_listeners:
            listener(self)

    def set_incoming_beam(self, incoming_beam):
        """
        Set the incoming beam for the component setpoint calculation
        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        self._incoming_beam = incoming_beam
        self._trigger_after_beam_path_update()

    def get_outgoing_beam(self):
        """
        Returns the outgoing beam. This class is overridden by components which affect the beam angle.
        Returns (PositionAndAngle): the outgoing beam based on the incoming beam and any interaction with the component
        """
        return self._incoming_beam

    def calculate_beam_interception(self):
        """
        Returns: the position at the point where the components possible movement intercepts the beam

        """
        return self._movement_strategy.calculate_interception(self._incoming_beam)

    def set_position_relative_to_beam(self, displacement):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            displacement: the value to set away from the beam, e.g. height
        """
        self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam, displacement)
        self._trigger_after_beam_path_update()

    def get_position_relative_to_beam(self):
        """

        Returns: the displacement of the component relative to the beam, E.g. The distance along the movement
            axis of the component from the intercept with the beam.

        """
        return self._movement_strategy.get_distance_relative_to_beam(self._incoming_beam)

    def set_displacement(self, displacement, alarm_severity, alarm_status):
        """
        Set the displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        Args:
            displacement: the displacement to set
            alarm_severity (ReflectometryServer.pv_wrapper.AlarmSeverity): severity of any alarm
            alarm_status (ReflectometryServer.pv_wrapper.AlarmCondition): the alarm status
        """
        self._movement_strategy.set_displacement(displacement)
        self._trigger_after_beam_path_update()
        self._trigger_after_physical_move_listener()

    def get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        return self._movement_strategy.get_displacement()

    def sp_position(self):
        """
        Returns (Position): The set point position of this component in mantid coordinates.
        """
        return self._movement_strategy.sp_position()

    @property
    def is_in_beam(self):
        """
        Returns: the enabled status
        """
        return self._is_in_beam

    @is_in_beam.setter
    def is_in_beam(self, is_in_beam):
        """
        Updates the components in_beam status and notifies the beam path update listener
        Args:
            is_in_beam: True if set the component to be in the beam; False otherwise
        """
        self._is_in_beam = is_in_beam
        self._trigger_after_beam_path_update()
        self._trigger_after_physical_move_listener()

    def add_after_physical_move_listener(self, listener):
        """
        Add a listener which is called when a move is generated from a location change not from a incoming beam path
        change. For example when a height is increased by the motor. This is used by the Theta readback to determine if
        a component has changed height.
        Args:
            listener: listener takes the source of the change
        """
        self._after_physical_move_listeners.add(listener)

    def _trigger_after_physical_move_listener(self):
        for listener in self._after_physical_move_listeners:
            listener(self)


class _BeamPathCalcWithAngle(TrackingBeamPathCalc):
    def __init__(self, movement_strategy):
        super(_BeamPathCalcWithAngle, self).__init__(movement_strategy)
        self._angle = 0.0

    def _set_angle(self, angle):
        """
        Set the angle
        Args:
            angle: angle to set
        """
        self._angle = angle
        self._trigger_after_beam_path_update()

    def set_angle_relative_to_beam(self, angle):
        """
        Set the angle of the component relative to the beamline
        Args:
            angle: angle to set the component at
        """
        self._set_angle(angle + self._incoming_beam.angle)

    def get_angle_relative_to_beam(self):
        """
        Returns: the angle of the component relative to the beamline
        """
        return self._angle - self._incoming_beam.angle


class BeamPathTilting(_BeamPathCalcWithAngle):
    """
    A beam path calculation which includes an angle it can tilt at. Beam path is unaffected by the angle.
    """
    def __init__(self, movement_strategy):
        super(BeamPathTilting, self).__init__(movement_strategy)

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle

    @angle.setter
    def angle(self, angle):
        """
        Updates the component angle and notifies the beam path update listener
        Args:
            angle: The modified angle
        """
        self._set_angle(angle)
        self._trigger_after_physical_move_listener()


class _BeamPathCalcReflecting(_BeamPathCalcWithAngle):
    """
    A beam path calculation which includes an angle of the component and that reflects the beam from that angle.
    This is used for theta and reflecting component.
    """
    def __init__(self, movement_strategy):
        super(_BeamPathCalcReflecting, self).__init__(movement_strategy)

    def get_outgoing_beam(self):
        """
        Returns: the outgoing beam based on the last set incoming beam and any interaction with the component
        """
        if not self._is_in_beam:
            return self._incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angle - self._incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self._incoming_beam.angle
        return PositionAndAngle(target_position.y, target_position.z, angle)


class BeamPathCalcAngleReflecting(_BeamPathCalcReflecting):
    """
    A reflecting beam path calculation which includes an angle of the component that can be set,
    e.g. a reflecting mirror.
    """
    def __init__(self, movement_strategy):
        super(BeamPathCalcAngleReflecting, self).__init__(movement_strategy)
        self._angle = 0.0

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle

    @angle.setter
    def angle(self, angle):
        """
        Updates the component angle and notifies the beam path update listener
        Args:
            angle: The modified angle
        """
        self._set_angle(angle)
        self._trigger_after_physical_move_listener()


class BeamPathCalcTheta(_BeamPathCalcReflecting):
    """
    A reflecting beam path calculator which has a read only angle based on the angle to a list of beam path
    calculations. This is used for example for Theta where the angle is the angle to the next enabled component
    """
    def __init__(self, movement_strategy, angle_to):
        """
        Initialiser.
        Args:
            movement_strategy: movement strategy to use
            angle_to (list[ReflectometryServer.beam_path_calc.TrackingBeamPathCalc]):
                beam path calc on which to base the angle
        """
        super(BeamPathCalcTheta, self).__init__(movement_strategy)
        self._angle_to = angle_to
        for readback_beam_path_calc in self._angle_to:
            readback_beam_path_calc.add_after_physical_move_listener(self._update_angle)

    def _update_angle(self, source):
        """
        A listener for the beam update from another beam calc.
        Args:
            source: the beam calc that changed
        """
        self._set_angle(self._calc_angle_from_next_component(self._incoming_beam))

    def _calc_angle_from_next_component(self, incoming_beam):
        """
        Calculates the angle needed for a mirror to be position to reflect the incoming beam to the components position.

        Returns: half the angle to the next enabled beam path calc, or nan if there isn't one.
        """
        for readback_beam_path_calc in self._angle_to:
            if readback_beam_path_calc.is_in_beam:
                other_pos = readback_beam_path_calc.sp_position()
                this_pos = self._movement_strategy.calculate_interception(incoming_beam)

                opp = other_pos.y - this_pos.y
                adj = other_pos.z - this_pos.z
                # x = degrees(atan2(opp, adj)) is angle in room co-ords to component
                # x = x - incoming_beam.angle : is 2 theta
                # x = x / 2.0: is theta
                # x + incoming_beam.angle: angle of sample in room coordinate

                angle = (degrees(atan2(opp, adj)) - incoming_beam.angle) / 2.0 + incoming_beam.angle
                break
        else:
            angle = float("NaN")
        return angle

    def set_incoming_beam(self, incoming_beam):
        """
        Set the incoming beam for the component setpoint calculation
        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        self._angle = self._calc_angle_from_next_component(incoming_beam)
        super(BeamPathCalcTheta, self).set_incoming_beam(incoming_beam)

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle
