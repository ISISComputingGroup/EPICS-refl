"""
Parameters that the user would interact with
"""
from enum import Enum


class BeamlineParameterType(Enum):
    """
    Types of beamline parameters
    """
    FLOAT = 0
    IN_OUT = 1


class BeamlineParameterGroup(Enum):
    """
    Types of groups a parameter can belong to
    """
    TRACKING = 1


class BeamlineParameter(object):
    """
    General beamline parameter that can be set. Subclass must implement _calc_move to decide what to do with the
    value that is set.
    """

    def __init__(self, name, sim=False, init=None):
        if sim:
            self._set_point = init
            self._set_point_rbv = init
        else:
            self._set_point = None
        self._sp_is_changed = False
        self._name = name
        self.after_move_listener = lambda x: None
        self.parameter_type = BeamlineParameterType.FLOAT
        self.group_names = []

    @property
    def sp_rbv(self):
        """
        Returns: the set point read back value, i.e. where the last move was instructed to go
        """
        return self._set_point_rbv

    @property
    def sp_no_move(self):
        """
        The set point of where it will move to when move is set.

        Returns: Setpoint last set, i.e. when the next move on this parameter is called where it will move to
        """
        return self._set_point

    @sp_no_move.setter
    def sp_no_move(self, set_point):
        """
        The set point of where it will move to when move is set.
        Move is not done this is mainly for use in the OPI.
        Args:
            set_point: the set point
        """
        self._set_point = set_point
        self._sp_is_changed = True

    @property
    def sp(self):
        """
        Move to this setpoint.
        Returns: Setpoint last set, i.e. when the next move on this parameter is called where it will move to
        """
        return self._set_point

    @sp.setter
    def sp(self, value):
        """
        Set the set point and move to it.
        Args:
            value: new set point
        """
        self.sp_no_move = value
        self.move = 1

    @property
    def move(self):
        """
        Move to the setpoint.
        """
        return 0

    @move.setter
    def move(self, _):
        """
        Move to the setpoint, no matter what the value passed is.
        """
        self.move_no_callback()
        self.after_move_listener(self)

    def move_no_callback(self):
        """
        Move the component but don't call a callback indicating a move has been performed.
        """
        self._move_component()
        self._set_point_rbv = self._set_point
        self._sp_is_changed = False

    @property
    def name(self):
        """
        Returns: name of this beamline parameter
        """
        return self._name

    @property
    def sp_changed(self):
        """
        Returns: Has set point been changed since the last move
        """
        return self._sp_is_changed

    def _move_component(self):
        """
        Moves the component(s) associated with this parameter to the setpoint.
        """
        raise NotImplemented("This must be implement in the sub class")


class ReflectionAngle(BeamlineParameter):
    """
    The angle of the mirror measured from the incoming beam.
    Angle is measure with +ve in the anti-clockwise direction)
    """

    def __init__(self, name, reflection_component, sim=False, init=0):
        """
        Initializer.
        Args:
            name (str): Name of the reflection angle
            reflection_component (ReflectometryServer.components.ReflectingComponent): the active component at the
                reflection point
        """
        super(ReflectionAngle, self).__init__(name, sim, init)
        self._reflection_component = reflection_component

    def _move_component(self):
        self._reflection_component.set_angle_relative_to_beam(self._set_point)


class Theta(ReflectionAngle):
    """
    Twice the angle between the incoming beam and outgoing beam at the ideal sample point.
    Angle is measure with +ve in the anti-clockwise direction (opposite of room coordinates)
    """

    def __init__(self, name, ideal_sample_point, sim=False, init=0):
        """
        Initializer.
        Args:
            name (str): name of theta
            ideal_sample_point (ReflectometryServer.components.ReflectingComponent): the ideal sample point active component
        """
        super(Theta, self).__init__(name, ideal_sample_point, sim, init)


class TrackingPosition(BeamlineParameter):
    """
    Component which tracks the position of the beam with a single degree of freedom. E.g. slit set on a height stage
    """

    def __init__(self, name, component, sim=False, init=0):
        """

        Args:
            name: Name of the variable
            component (ReflectometryServer.components.PassiveComponent): component that the tracking is based on
        """
        super(TrackingPosition, self).__init__(name, sim, init)
        self._component = component
        self.group_names.append(BeamlineParameterGroup.TRACKING)

    def _move_component(self):
        self._component.set_position_relative_to_beam(self._set_point)


class ComponentEnabled(BeamlineParameter):
    """
    Parameter which sets whether a given device is enabled (i.e. parked in beam) on the beamline.
    """

    def __init__(self, name, component, sim=False, init=False):
        """
        Initializer.
        Args:
            name (str): Name of the enabled parameter
            component (ReflectometryServer.components.PassiveComponent): the component to be enabled or disabled
        """
        super(ComponentEnabled, self).__init__(name, sim, init)
        self._component = component
        self.parameter_type = BeamlineParameterType.IN_OUT

    def _move_component(self):
        self._component.enabled = self._set_point
