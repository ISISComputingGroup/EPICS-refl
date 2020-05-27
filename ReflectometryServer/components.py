"""
Components on a beam
"""
from collections import namedtuple

from pcaspy import Severity

from ReflectometryServer.exceptions import BeamlineConfigurationInvalidException
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo
from server_common.observable import observable

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


# Event that happens when a value is redefine to a different value, e.g. offset is set from 2 to 3
DefineValueAsEvent = namedtuple("DefineValueAsEvent", [
    "new_position",  # the new value
    "change_axis"])  # the axis it applies to of type ChangeAxis


@observable(DefineValueAsEvent)
class Component:
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
        self.can_define_current_angle_as = False

    def __repr__(self):
        return "{}({} beampath sp:{!r}, beampath rbv:{!r})), ".format(
            self.__class__.__name__, self._name, self._beam_path_set_point, self._beam_path_rbv)

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = TrackingBeamPathCalc("{}_sp".format(self.name), LinearMovementCalc(setup))
        self._beam_path_rbv = TrackingBeamPathCalc("{}_rbv".format(self.name), LinearMovementCalc(setup))

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
            STATUS_MANAGER.update_error_log(
                "Tried to read an invalid type of parameter for component {}.".format(self.name))
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Tried to read invalid component axis", self.name, Severity.MINOR_ALARM))
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

    def set_incoming_beam_can_change(self, can_change, on_init=False):
        """
        Set whether the incoming beam can be changed on a component. This is used in disable mode where the incoming
        beam can not be changed.
        Args:
            can_change: True if the incoming beam can changed; False if it is static
            on_init: True if initialising the beam can change parameter; False otherwise
        """
        self._beam_path_set_point.incoming_beam_can_change = can_change
        self._beam_path_rbv.incoming_beam_can_change = can_change

        if on_init:
            self._beam_path_set_point.init_from_autosave()
            self._beam_path_rbv.init_from_autosave()
        else:
            self._beam_path_set_point.incoming_beam_auto_save()
            self._beam_path_rbv.incoming_beam_auto_save()

    def define_current_position_as(self, new_value):
        """
        Define the current position of the component as the given value (e.g. set this in the motor)
        Args:
            new_value: new value of the position
        """
        motor_displacement = self.beam_path_rbv.get_displacement_for(new_value)
        self.trigger_listeners(DefineValueAsEvent(motor_displacement, ChangeAxis.POSITION))


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
        self.can_define_current_angle_as = True

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name), LinearMovementCalc(setup),
                                                                  is_reflecting=False)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name), LinearMovementCalc(setup),
                                                            is_reflecting=False)

    def define_current_angle_as(self, new_angle):
        """
        Define the current angle of the component as the given value (e.g. set this in the motor)

        Args:
            new_angle (float): new angle of the component
        """
        room_angle = self._beam_path_rbv.get_angle_for(new_angle)
        self.trigger_listeners(DefineValueAsEvent(room_angle, ChangeAxis.ANGLE))


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
        self.can_define_current_angle_as = True

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name), LinearMovementCalc(setup),
                                                                  is_reflecting=True)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name), LinearMovementCalc(setup),
                                                            is_reflecting=True)

    def define_current_angle_as(self, new_angle):
        """
        Define the current angle of the component as the given value (e.g. set this in the motor)

        Args:
            new_angle (float): new angle of the component
        """
        room_angle = self._beam_path_rbv.get_angle_for(new_angle)
        self.trigger_listeners(DefineValueAsEvent(room_angle, ChangeAxis.ANGLE))


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
        self.can_define_current_angle_as = False

    def _init_beam_path_calcs(self, setup):
        linear_movement_calc = LinearMovementCalc(setup)

        angle_to_for_sp = [comp.beam_path_set_point for comp in self.angle_to_components]
        angle_to_for_rbv = [(comp.beam_path_rbv, comp.beam_path_set_point) for comp in self.angle_to_components]

        self._beam_path_set_point = BeamPathCalcThetaSP("{}_sp".format(self.name), linear_movement_calc, angle_to_for_sp)
        self._beam_path_rbv = BeamPathCalcThetaRBV("{}_rbv".format(self.name), linear_movement_calc,
                                                   self._beam_path_set_point, angle_to_for_rbv)

    def define_current_angle_as(self, new_angle):
        """
        Define the current angle for the component in the hardware

        Args:
            new_angle (float): new angle to use

        Raises: This is not allowed for Theta at this time because of the complexity of coding this, and we don't think
        it is needed since the scan is done over detector offset and detector angle.

        """
        raise NotImplementedError("Can not set Theta at a given value")


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
