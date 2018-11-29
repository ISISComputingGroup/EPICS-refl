"""
Objects to help with calculating the beam path when interacting with a component. This is used for instance for the
set points or readbacks etc.
"""
from math import degrees, atan2

from ReflectometryServer.geometry import PositionAndAngle


class TrackingBeamPathCalc(object):
    """
    Calculator for the beam path when it interacts with a component that can track the beam.
    """

    def __init__(self, movement_strategy):
        """
        Initialiser.
        Args:
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovementCalc): strategy for calculating the
                interception between the movement of the
        """
        self._incoming_beam = None
        self._after_beam_path_update_listener = set()
        self._enabled = True
        self._movement_strategy = movement_strategy

    def add_after_beam_path_update_listener(self, listen_for_value):
        """
        Add a listener which is triggered if the beam path is changed. For example if displacement is set or incoming
        beam is changed.
        Args:
            listen_for_value: listener with a single argument which is the calling calculation.
        """
        self._after_beam_path_update_listener.add(listen_for_value)

    def _trigger_after_beam_path_update(self):
        """
        Runs all the current listeners because something about the beam path has changed.
        """
        for listener in self._after_beam_path_update_listener:
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

        self._movement_strategy.set_position_relative_to_beam(self._incoming_beam, displacement)
        self._trigger_after_beam_path_update()

    def get_position_relative_to_beam(self):
        """

        Returns: the displacement of the component relative to the beam, E.g. The distance along the movement
            axis of the component from the intercept with the beam.

        """
        return self._movement_strategy.get_displacement_relative_to_beam(self._incoming_beam)

    def set_displacement(self, displacement):
        """
        Set the displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        Args:
            displacement: the displacement to set
        """
        self._movement_strategy.set_displacement(displacement)
        self._trigger_after_beam_path_update()

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
    def enabled(self):
        """
        Returns: the enabled status
        """
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        """
        Updates the component enabled status and notifies the beam path update listener
        Args:
            enabled: The modified enabled status
        """
        self._enabled = enabled
        self._trigger_after_beam_path_update()


class BeamPathTiltingJaws(TrackingBeamPathCalc):
    """
    A beam path which includes a jaw which will title at 90 degrees to the jaw
    """
    component_to_beam_angle = 90

    def __init__(self, movement_strategy):
        super(BeamPathTiltingJaws, self).__init__(movement_strategy)
        self._angle = 0.0

    def calculate_tilt_angle(self):
        """
        Returns: the angle to tilt so the jaws are perpendicular to the beam.
        """
        return self._incoming_beam.angle + self.component_to_beam_angle


class _BeamPathCalcAngle(TrackingBeamPathCalc):
    """
    A beam path calculation which includes an angle of the component, but not a way of setting the angle externally.
    This is used for theta and reflecting component.
    """
    def __init__(self, movement_strategy):
        super(_BeamPathCalcAngle, self).__init__(movement_strategy)
        self._angle = None

    def _set_angle(self, angle):
        """
        Set the angle
        Args:
            angle: angle to set
        """
        self._angle = angle
        self._trigger_after_beam_path_update()

    def get_outgoing_beam(self):
        """
        Returns: the outgoing beam based on the last set incoming beam and any interaction with the component
        """
        if not self._enabled:
            return self._incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angle - self._incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self._incoming_beam.angle
        return PositionAndAngle(target_position.y, target_position.z, angle)

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


class BeamPathCalcAngle(_BeamPathCalcAngle):
    """
    A beam path calculation which includes an angle of the component, e.g. a reflecting mirror.
    """
    def __init__(self, movement_strategy):
        super(BeamPathCalcAngle, self).__init__(movement_strategy)
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


class BeamPathCalcTheta(_BeamPathCalcAngle):
    """
    A beam path calculator which has a read only angle based on the angle to a list of beam path calculations. This is
    used for example for Theta where the angle is the angle to the next enabled component
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
        self._angle = self._calc_angle_from_next_component()
        for readback_beam_path_calc in self._angle_to:
            readback_beam_path_calc.add_after_beam_path_update_listener(self._update_angle)

    def _update_angle(self, source):
        """
        A listener for the beam update from another beam calc.
        Args:
            source: the beam calc that changed
        """
        self._set_angle(self._calc_angle_from_next_component())

    def _calc_angle_from_next_component(self):
        """
        Returns: the angle to the next enabled beam path calc, or nan if there isn't one.
        """
        for readback_beam_path_calc in self._angle_to:
            if readback_beam_path_calc.enabled:
                other_pos = readback_beam_path_calc.sp_position()
                this_pos = self.sp_position()
                opp = other_pos.y - this_pos.y
                adj = other_pos.z - this_pos.z
                angle = degrees(atan2(opp, adj))
                break
        else:
            angle = float("NaN")
        return angle

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle
