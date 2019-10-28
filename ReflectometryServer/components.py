"""
Components on a beam
"""
from enum import Enum
from ReflectometryServer.beam_path_calc import TrackingBeamPathCalc, SettableBeamPathCalcWithAngle, \
    BeamPathCalcThetaRBV, BeamPathCalcThetaSP
from ReflectometryServer.movement_strategy import LinearMovementCalc
import logging

logger = logging.getLogger(__name__)


class ChangeAxis(Enum):
    """
    Types of axes in the component that can change.
    """
    POSITION = 0
    ANGLE = 1


class Component(object):
    """
    Base object for all components that can sit on a beam line
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        self._name = name
        self._init_beam_path_calcs(setup)
        self._changed = {ChangeAxis.POSITION: False}

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = TrackingBeamPathCalc(LinearMovementCalc(setup))
        self._beam_path_rbv = TrackingBeamPathCalc(LinearMovementCalc(setup))

    def set_changed_flag(self, change_type, value):
        """
        Set a flag signalling whether this component has an un-applied change.

        Params:
            change_type (ChangeType): The type of axis for which to set the flag
            value (bool): Value to set or clear the flag
        """
        self._changed[change_type] = value

    def read_changed_flag(self, change_axis):
        """
        Reads a flag signalling whether this component has an un-applied change.

        Params:
            change_axis (ChangeAxis): The type of axis for which to read the flag

        Returns: Whether the flag for the given axis has changed
        """
        try:
            return self._changed[change_axis]
        except KeyError:
            logger.error("Tried to read an invalid type of parameter for component {}.".format(self.name))
            return True

    @property
    def name(self):
        """
        Returns: Name of the component
        """
        return self._name

    @property
    def beam_path_set_point(self):
        """
        The beam path calculation for the set points. This is readonly and can only be set during construction
        Returns:
            (TrackingBeamPathCalc|SettableBeamPathCalcWithAngle|BeamPathCalcThetaRBV|BeamPathCalcThetaSP|BeamPathCalcAngleReflecting):
                set points beam path calculation
        """
        return self._beam_path_set_point

    @property
    def beam_path_rbv(self):
        """
        The beam path calculation for the read backs. This is readonly and can only be set during construction
        Returns:
            (TrackingBeamPathCalc|SettableBeamPathCalcWithAngle|BeamPathCalcThetaRBV|BeamPathCalcThetaSP|BeamPathCalcAngleReflecting):
                read backs beam path calculation

        """
        return self._beam_path_rbv

    def set_incoming_beam_can_change(self, can_change):
        """
        Set whether the incoming beam can be changed on a component. This is used in disable mode where the incoming
        beam can not be changed.
        Args:
            can_change: True if the incoming beam can changed; False if it is static
        """
        self._beam_path_set_point.incoming_beam_can_change = can_change
        self._beam_path_rbv.incoming_beam_can_change = can_change


class TiltingComponent(Component):
    """
    Component which can tilt.
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(TiltingComponent, self).__init__(name, setup)
        self._changed[ChangeAxis.ANGLE] = False

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle(LinearMovementCalc(setup), is_reflecting=False)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle(LinearMovementCalc(setup), is_reflecting=False)


class ReflectingComponent(Component):
    """
    Components which reflects the beam from an reflecting surface at an angle.
    """
    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(ReflectingComponent, self).__init__(name, setup)
        self._changed[ChangeAxis.ANGLE] = False

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle(LinearMovementCalc(setup), is_reflecting=True)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle(LinearMovementCalc(setup), is_reflecting=True)


class ThetaComponent(ReflectingComponent):
    """
    Components which reflects the beam from an reflecting surface at an angle.
    """

    def __init__(self, name, setup, angle_to):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
            angle_to (list[ReflectometryServer.components.Component]): list of components that the readback
                angle should calculated to, ordered by preference. First enabled component is used.
        """
        self.angle_to_components = angle_to
        super(ReflectingComponent, self).__init__(name, setup)

    def _init_beam_path_calcs(self, setup):
        beam_path_calcs = [(comp.beam_path_rbv, comp.beam_path_set_point) for comp in self.angle_to_components]
        linear_movement_calc = LinearMovementCalc(setup)
        self._beam_path_set_point = BeamPathCalcThetaSP(linear_movement_calc,
                                                        [comp.beam_path_set_point for comp in self.angle_to_components])
        self._beam_path_rbv = BeamPathCalcThetaRBV(linear_movement_calc, beam_path_calcs, self._beam_path_set_point)


# class Bench(Component):
#     """
#     Jaws which can tilt.
#     """
#     def __init__(self, name, centre_of_rotation_z, distance_from_sample_to_bench):
#
#         super(Bench, self).__init__(name, ArcMovement(centre_of_rotation_z))
#         self.distance_from_sample_to_bench = distance_from_sample_to_bench
#
#     def calculate_front_position(self):
#         """
#         Returns: the angle to tilt so the jaws are perpendicular to the beam.
#         """
#         center_of_rotation = self.calculate_beam_interception()
#         x = center_of_rotation.z + self.distance_from_sample_to_bench * cos(self.incoming_beam.angle)
#         y = center_of_rotation.y + self.distance_from_sample_to_bench * sin(self.incoming_beam.angle)
#         return Position(y, x)
