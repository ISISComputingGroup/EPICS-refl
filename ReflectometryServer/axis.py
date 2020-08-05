from abc import ABCMeta, abstractmethod
from collections import namedtuple
from dataclasses import dataclass


from server_common.channel_access import AlarmStatus, AlarmSeverity
from server_common.observable import observable

PhysicalMoveUpdate = namedtuple("PhysicalMoveUpdate", [
    "source"])  # The source of the beam path change. (the axis itself)
AxisChangingUpdate = namedtuple("AxisChangingUpdate", [])
InitUpdate = namedtuple("InitUpdate", [])
DefineValueAsEvent = namedtuple("DefineValueAsEvent", [
    "new_position",  # the new value
    "change_axis"])  # the axis it applies to of type ChangeAxis


@dataclass()
class AxisChangedUpdate:
    """
    Event when changed if updated
    """
    is_changed_update: bool  # True if there is an unapplied updated; False otherwise


@dataclass()
class SetRelativeToBeamUpdate:
    """
    Event when relative to beam has been updated
    """
    relative_to_beam: float


@observable(DefineValueAsEvent, AxisChangingUpdate, PhysicalMoveUpdate, InitUpdate, AxisChangedUpdate,
            SetRelativeToBeamUpdate)
class ComponentAxis(metaclass=ABCMeta):
    """
    A components axis of movement, allowing setting in both mantid and relative coordinates. Transmits alarms,
    changed and changes.
    """

    def __init__(self, axis):
        """
        Initialisation.

        Args:
            axis: axis that the component is for
        """
        self._is_changing = False
        self.autosaved_value = None
        self._is_changed = False
        self._axis = axis
        self._alarm = (AlarmSeverity.Invalid, AlarmStatus.UDF)
        self.can_define_axis_position_as = False

    @abstractmethod
    def get_relative_to_beam(self):
        """
        Returns: position relative to the incoming beam
        """
        pass

    def set_relative_to_beam(self, value):
        """
        Set a axis value relative to the beam, e.g. position relative to the beam.
        Args:
            value: value to set
        """
        self.is_changed = True
        self.on_set_relative_to_beam(value)
        self.trigger_listeners(SetRelativeToBeamUpdate(value))

    @abstractmethod
    def on_set_relative_to_beam(self, value):
        """
        Set a axis value relative to the beam, e.g. position relative to the beam. But without triggers event or
        setting is_changed
        Args:
            value: value to set
        """

    def set_alarm(self, alarm_severity, alarm_status):
        """
        Update the alarm info for the angle axis of this component.

        Args:
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmStatus): the alarm status
        """
        self._alarm = (alarm_severity, alarm_status)

    @abstractmethod
    def _get_displacement_for(self, position_relative_to_beam):
        """
        Get the displacement for a given position relative to the beam
        Args:
            position_relative_to_beam: position relative to the beam

        Returns:
            displacement in mantid coordinates
        """

    def define_axis_position_as(self, new_value):
        """
        Define the current position of the axis as the given value (e.g. set this in the motor)
        Args:
            new_value: new value of the position relative to the beam
        """
        if self.can_define_axis_position_as:
            axis_displacement = self._get_displacement_for(new_value)
            self.trigger_listeners(DefineValueAsEvent(axis_displacement, self._axis))
        else:
            raise TypeError("Axis can not have its position defined")

    @abstractmethod
    def get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        pass

    def set_displacement(self, update):
        """
        Update the driver axis from mantid coordinates, e.g. motor position
        Including the alarm and trigger a physical move event
        Args:
            update (ReflectometryServer.ioc_driver.CorrectedReadbackUpdate): pv update for this axis
        """
        self.set_alarm(update.alarm_severity, update.alarm_status)
        self._on_set_displacement(update.value)
        self.trigger_listeners(PhysicalMoveUpdate(self))

    @abstractmethod
    def _on_set_displacement(self, displacement):
        """
        Update the driver axis from mantid coordinates, e.g. motor position
        Called from set displacement after setting alarms and before triggering physical movement
        Args:
            displacement (float): displacement in mantid coordinates
        """

    @abstractmethod
    def init_displacement_from_motor(self, value):
        """
        Sets the displacement read from the motor axis on startup.

        Args:
            value(float): The motor position
        """
        pass

    @property
    def is_changing(self):
        """
        Returns: Is the component with angle currently rotating
        """
        return self._is_changing

    @is_changing.setter
    def is_changing(self, value):
        """
         Update the changing state of the component and notifies relevant listeners. Changing is usually caused by
         the motor axis moving.

         Args:
             value: the new rotating state
        """
        self._is_changing = value
        self.trigger_listeners(AxisChangingUpdate())

    @property
    def alarm(self):
        """
        Returns:
            the alarm tuple for the axis, alarm_severity and alarm_status
        """
        return self._alarm

    @property
    def is_changed(self):
        """
        Reads a flag signalling whether this axis has an un-applied change.

        Returns:
            True axis has un-applied changed; False otherwise
        """
        return self._is_changed

    @is_changed.setter
    def is_changed(self, is_changed):
        """
        Set a flag signalling whether this axis has an un-applied change.

        Args:
            is_changed (bool): True axis has un-applied changed; False otherwise
        """
        self._is_changed = is_changed
        self.trigger_listeners(AxisChangedUpdate(is_changed))


class DirectCalcAxis(ComponentAxis):
    """
    Directly connect the relative and the mantid coordinates together
    """
    def __init__(self, axis):
        super(DirectCalcAxis, self).__init__(axis)
        self.can_define_axis_position_as = True
        self._position = 0.0

    def get_relative_to_beam(self):
        """
        Returns: value of the axis
        """
        return self._position

    def on_set_relative_to_beam(self, position):
        """
        Set an axis position
        Args:
            position: position to set
        """
        self._position = position

    def _get_displacement_for(self, position_relative_to_beam):
        """
        Get a displacement for a given position
        Args:
            position_relative_to_beam: position of axis

        Returns:
            position in mantid coordinates
        """
        return position_relative_to_beam

    def get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        return self._position

    def _on_set_displacement(self, displacement):
        """
        Update the driver axis from mantid coordinates, e.g. motor position
        Called from set displacement after setting alarms and before triggering physical movement
        Args:
            displacement (float): displacement in mantid coordinates
        """
        self._position = displacement

    def init_displacement_from_motor(self, motor_position):
        """
        Sets the displacement read from the motor axis on startup.

        Args:
            motor_position (float): The motor position
        """
        self._position = motor_position
        self.trigger_listeners(InitUpdate())  # Tell Parameter layer and Theta


class BeamPathCalcAxis(ComponentAxis):
    """
    Axes for a component for the beam path calc. Used to setup for either the position and angle axis.

    This is basically a thin layer that calls the function on the axis and then delegates to the beam path calc. This
    object is initialised with the functions to call.
    """
    def __init__(self, axis, get_relative_to_beam, set_relative_to_beam, get_displacement_for=None,
                 get_displacement=None, set_displacement=None, init_displacement_from_motor=None):
        """
        Initialiser.
        Args:
            axis: the axis this object is of
            get_relative_to_beam: function returning this axis position relative to the components incoming beam
            set_relative_to_beam: function setting this axis position relative to the components incoming beam
            get_displacement_for: get a displacement for a position relative to the beam
            get_displacement: function to return the axis displacement in mantid coordinates
            set_displacement: function to update the displacement from the motor; None for can not be set
            init_displacement_from_motor: function to set the initial displacement based on the motor, for set points;
                None for can not be set
        """
        super().__init__(axis)
        self._get_relative_to_beam = get_relative_to_beam
        self._set_relative_to_beam = set_relative_to_beam
        self._get_displacement_for_fn = get_displacement_for
        self.can_define_axis_position_as = get_displacement_for is not None

        self._get_displacement = get_displacement
        self._set_displacement = set_displacement
        self._init_displacement_from_motor = init_displacement_from_motor

    def _get_displacement_for(self, position_relative_to_beam):
        return self._get_displacement_for_fn(position_relative_to_beam)

    def get_relative_to_beam(self):
        """
        Returns: position relative to the incoming beam
        """
        return self._get_relative_to_beam()

    def on_set_relative_to_beam(self, value):
        """
        Set a axis value relative to the beam, e.g. position relative to the beam.
        Args:
            value: value to set
        """
        return self._set_relative_to_beam(value)

    def get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        if self._get_displacement is not None:
            return self._get_displacement()
        raise TypeError("Axis does not support get_displacement")

    def _on_set_displacement(self, displacement):
        """
        Update the driver axis from mantid coordinates, e.g. motor position
        Args:
            displacement (float): pv update for this axis
        """
        if self._set_displacement is not None:
            return self._set_displacement(displacement)
        raise TypeError("Axis does not support set_displacement")

    def init_displacement_from_motor(self, value):
        """
        Sets the displacement read from the motor axis on startup.

        Args:
            value(float): The motor position
        """
        if self._init_displacement_from_motor is not None:
            return self._init_displacement_from_motor(value)
        raise TypeError("Axis does not support init_displacement_from_motor")
