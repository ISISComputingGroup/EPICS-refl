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
    General beamline parameter that can be set. Subclass must implement _move_component to decide what to do with the
    value that is set.
    """
    def __init__(self, name, sim=False, init=None, description=None):
        if sim:
            self._set_point = init
            self._set_point_rbv = init
        else:
            self._set_point = None
            self._set_point_rbv = None
        self._sp_is_changed = False
        self._name = name
        self.after_move_listener = lambda x: None
        self.parameter_type = BeamlineParameterType.FLOAT
        if description is None:
            self.description = name
        else:
            self.description = description
        self.group_names = []
        self._rbv_change_listeners = set()

    def __repr__(self):
        return "{} '{}': sp={}, sp_rbv={}, rbv={}, changed={}".format(__name__, self.name, self._set_point,
                                                                      self._set_point_rbv, self.rbv, self.sp_changed)

    @property
    def rbv(self):
        """
        Returns: the read back value
        """
        return self._rbv()

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
        self._sp_no_move(set_point)

    def _sp_no_move(self, set_point):
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
        self._sp_no_move(value)
        self._do_move()

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
        self._do_move()

    def _do_move(self):
        self.move_to_sp_no_callback()
        self.after_move_listener(self)

    def move_to_sp_no_callback(self):
        """
        Move the component but don't call a callback indicating a move has been performed.
        """
        self._set_point_rbv = self._set_point
        self._move_component()
        self._sp_is_changed = False

    def move_to_sp_rbv_no_callback(self):
        """
        Repeat the move to the last set point.
        """
        self._move_component()

    def add_rbv_change_listener(self, listener):
        """
        Add a listener which should be called if the rbv value changes.
        Args:
            listener: the function to call with one argument which is the new rbv value
        """
        self._rbv_change_listeners.add(listener)

    def _trigger_rbv_listeners(self, source):
        """
        Trigger all rbv listeners

        Args:
            source: source of change which is not used
        """
        rbv = self._rbv()
        for listener in self._rbv_change_listeners:
            listener(rbv)

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
        raise NotImplemented("This must be implemented in the sub class")

    def _rbv(self):
        """
        Returns: the read back value
        """
        raise NotImplemented("This must be implemented in the sub class")


class SlitGapParameter(BeamlineParameter):
    def __init__(self, name, pv_wrapper, sim=False, init=0, description=None):
        super(SlitGapParameter, self).__init__(name, sim, init, description)
        self._pv_wrapper = pv_wrapper

    def _move_component(self):
        self._pv_wrapper.sp_rbv = self._set_point

    def _rbv(self):
        return self._pv_wrapper.rbv

class AngleParameter(BeamlineParameter):
    """
    The angle of the component measured from the incoming beam, this could be theta, or the supermirror angle or
        title jaws angle.
    Angle is measure with +ve in the anti-clockwise direction)
    """

    def __init__(self, name, reflection_component, sim=False, init=0, description=None):
        """
        Initializer.
        Args:
            name (str): Name of the reflection angle
            reflection_component (ReflectometryServer.components.Component): the active component at the
                reflection point
            description (str): description
        """
        if description is None:
            description = "{} angle".format(name)
        super(AngleParameter, self).__init__(name, sim, init, description)
        self._reflection_component = reflection_component
        self._reflection_component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)

    def _move_component(self):
        self._reflection_component.beam_path_set_point.set_angle_relative_to_beam(self._set_point_rbv)

    def _rbv(self):
        return self._reflection_component.beam_path_rbv.get_angle_relative_to_beam()


class TrackingPosition(BeamlineParameter):
    """
    Component which tracks the position of the beam with a single degree of freedom. E.g. slit set on a height stage
    """

    def __init__(self, name, component, sim=False, init=0, description=None):
        """

        Args:
            name: Name of the variable
            component (ReflectometryServer.components.Component): component that the tracking is based on
            description (str): description
        """
        if description is None:
            description = "{} tracking position".format(name)
        super(TrackingPosition, self).__init__(name, sim, init, description=description)
        self._component = component
        self._component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)
        self.group_names.append(BeamlineParameterGroup.TRACKING)

    def _move_component(self):
        self._component.beam_path_set_point.set_position_relative_to_beam(self._set_point_rbv)

    def _rbv(self):
        """
        Returns: readback value for the tracking displacement above the beam
        """
        return self._component.beam_path_rbv.get_position_relative_to_beam()


class ComponentEnabled(BeamlineParameter):
    """
    Parameter which sets whether a given device is enabled (i.e. parked in beam) on the beamline.
    """

    def __init__(self, name, component, sim=False, init=False, description=None):
        """
        Initializer.
        Args:
            name (str): Name of the enabled parameter
            component (ReflectometryServer.components.Component): the component to be enabled or disabled
            description (str): description
        """
        if description is None:
            description = "{} component is in the beam".format(name)
        super(ComponentEnabled, self).__init__(name, sim, init, description=description)
        self._component = component
        self._component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)
        self.parameter_type = BeamlineParameterType.IN_OUT

    def _move_component(self):
        self._component.beam_path_set_point.enabled = self._set_point_rbv

    def _rbv(self):
        return self._component.beam_path_rbv.enabled
