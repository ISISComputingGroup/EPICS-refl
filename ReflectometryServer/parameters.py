"""
Parameters that the user would interact with
"""

from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union

from pcaspy import Severity
from server_common.utilities import SEVERITY

from ReflectometryServer.axis import SetRelativeToBeamUpdate

if TYPE_CHECKING:
    from ReflectometryServer.components import Component
    from ReflectometryServer.engineering_corrections import EngineeringCorrection
    from ReflectometryServer.ioc_driver import IocDriver

import abc
import logging
from enum import Enum

from server_common.channel_access import AlarmSeverity, AlarmStatus
from server_common.observable import observable

from ReflectometryServer.beam_path_calc import (
    AxisChangingUpdate,
    BeamPathUpdate,
    ComponentInBeamUpdate,
    InitUpdate,
    PhysicalMoveUpdate,
)
from ReflectometryServer.exceptions import ParameterNotInitializedException
from ReflectometryServer.file_io import (
    param_bool_autosave,
    param_float_autosave,
    param_string_autosave,
)
from ReflectometryServer.geometry import ChangeAxis
from ReflectometryServer.pv_wrapper import (
    IsChangingUpdate,
    JawsAxisPVWrapper,
    PVWrapper,
    ReadbackUpdate,
)
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo

DEFAULT_RBV_TO_SP_TOLERANCE = 0.002

logger = logging.getLogger(__name__)


# Thread pool for running custom user functions
CUSTOM_FUNCTION_POOL = ThreadPoolExecutor(max_workers=1)


@dataclass
class ParameterUpdateBase:
    """
    An update of a parameter used as a base for other events
    """

    value: Union[float, bool, str]  # The new value
    alarm_severity: [
        AlarmSeverity
    ]  # The alarm severity of the parameter, represented as an integer
    alarm_status: [AlarmStatus]  # The alarm status of the parameter, represented as an integer


@dataclass
class ParameterReadbackUpdate(ParameterUpdateBase):
    """
    An update of the parameter readback value
    """


@dataclass
class ParameterInitUpdate(ParameterReadbackUpdate):
    """
    An update that is triggered when the parameter has received an initial value either from autosave or motor rbv.
    """


@dataclass
class ParameterSetpointReadbackUpdate(ParameterReadbackUpdate):
    """
    An update of the parameter setpoint readback value
    """


@dataclass
class ParameterAtSetpointUpdate:
    """
    An update of the parameter at-setpoint state
    """

    value: bool  # The new state (boolean)


@dataclass
class ParameterChangingUpdate:
    """
    An update of the parameter is-changing state
    """

    value: bool  # The new state


@dataclass
class ParameterDisabledUpdate:
    """
    An update of the parameters is-disabled state
    """

    value: bool  # The new state


@dataclass
class RequestMoveEvent:
    """
    Called after a move has been requested on a parameter
    """

    source: "BeamlineParameter"  # beamline parameter which caused the move to be triggered


class DefineCurrentValueAsParameter:
    """
    A helper class which allows the current parameter readback to be set to a particular value by passing it down to the
    lower levels.
    """

    def __init__(self, define_current_value_as_fn, set_point_change_fn, parameter):
        self._new_value_sp_rbv = 0.0
        self._new_value_sp = 0.0
        self._changed = False
        self._define_current_value_as_fn = define_current_value_as_fn
        self._set_point_change_fn = set_point_change_fn
        self._parameter = parameter

    @property
    def new_value_sp_rbv(self):
        """
        Returns: The last value set
        """
        return self._new_value_sp_rbv

    @new_value_sp_rbv.setter
    def new_value_sp_rbv(self, value):
        """
        Set the new value and pass it down to the next layer
        Args:
            value: the new value to set the parameter to
        """
        logger.info(
            "Defining position for parameter {name} to {new_value}. "
            "From sp {sp}, sp_rbv {sp_rbv} and rbv {rbv}".format(
                name=self._parameter.name,
                new_value=value,
                sp=self._parameter.sp,
                sp_rbv=self._parameter.sp_rbv,
                rbv=self._parameter.rbv,
            )
        )

        self._new_value_sp_rbv = value
        self._define_current_value_as_fn(value)
        self._set_point_change_fn(value)

    @property
    def new_value_sp(self):
        return self._new_value_sp

    @new_value_sp.setter
    def new_value_sp(self, value):
        self._new_value_sp = value
        self._changed = True

    def do_action(self):
        self.new_value_sp_rbv = self.new_value_sp
        self._changed = False

    @property
    def changed(self):
        return self._changed


class BeamlineParameterType(Enum):
    """
    Types of beamline parameters
    """

    FLOAT = 0
    IN_OUT = 1
    ENUM = 2

    @staticmethod
    def name_for_param_list(param_type):
        """
        Returns: Type of parameter for the parameters list
        """
        if param_type is BeamlineParameterType.FLOAT:
            return "float"
        elif param_type is BeamlineParameterType.IN_OUT:
            return "in_out"
        elif param_type is BeamlineParameterType.ENUM:
            return "enum"
        else:
            raise ValueError("Parameter doesn't have recognised type {}".format(param_type))


class BeamlineParameterGroup(Enum):
    """
    Types of groups a parameter can belong to
    """

    ALL = 1
    COLLIMATION_PLANE = 2
    FOOTPRINT_PARAMETER = 3
    SLIT = 4
    TOGGLE = 5
    MISC = 6

    @staticmethod
    def description(parameter_group):
        """
        Description of the parameter group
        Args:
            parameter_group: parameter group enum

        Returns:
            Description of group
        """
        if parameter_group == BeamlineParameterGroup.ALL:
            return "All beamline parameters"
        elif parameter_group == BeamlineParameterGroup.COLLIMATION_PLANE:
            return "Axis Parameters in collimation plane"
        elif parameter_group == BeamlineParameterGroup.FOOTPRINT_PARAMETER:
            return "Parameters relevant to footprint calculation"
        elif parameter_group in [BeamlineParameterGroup.SLIT]:
            return "Slit parameters"
        elif parameter_group == BeamlineParameterGroup.TOGGLE:
            return "Toggle status parameters"
        elif parameter_group == BeamlineParameterGroup.MISC:
            return "Other beamline parameters"
        else:
            logger.error(
                "Unknown parameter group! {}".format(parameter_group),
                severity=SEVERITY.MAJOR,
                src="REFL",
            )
            return "(Unknown)"


@observable(
    ParameterReadbackUpdate,
    ParameterSetpointReadbackUpdate,
    ParameterAtSetpointUpdate,
    ParameterChangingUpdate,
    ParameterDisabledUpdate,
    ParameterInitUpdate,
    RequestMoveEvent,
)
class BeamlineParameter(metaclass=abc.ABCMeta):
    """
    General beamline parameter that can be set. Subclass must implement _move_component to decide what to do with the
    value that is set.
    """

    def __init__(
        self,
        name,
        description=None,
        autosave=True,
        rbv_to_sp_tolerance=0.01,
        custom_function: Optional[Callable[[Any, Any], str]] = None,
        characteristic_value="",
        sp_mirrors_rbv=False,
    ):
        """
        Initializer.
        Args:
            name: Name of the parameter
            description: description
            autosave: True if the parameter should be autosaved on change and read on start; False otherwise
            rbv_to_sp_tolerance: tolerance between the sp and rbv over which a warning should be indicated
            custom_function: custom function to run on move
            characteristic_value: PV which the user wants to group with this parameter; leave out for no value.
                This should not include the instrument prefix, e.g. MOT:MTR0101
            sp_mirrors_rbv: if True the sp gets set to the readback value when this parameter is asked to perform a
                move; False this doesn't happen
        """
        self._set_point = None
        self._set_point_rbv = None
        self.read_only = False

        self._sp_is_changed = False
        self._name = name
        self._is_disabled = False
        self._is_locked = False
        self.engineering_unit = ""
        self.alarm_status = None
        self.alarm_severity = None
        self.parameter_type = BeamlineParameterType.FLOAT
        self._add_to_parameter_groups()
        if description is None:
            self.description = name
        else:
            self.description = description
        self._autosave = autosave
        self._rbv_to_sp_tolerance = rbv_to_sp_tolerance

        self.define_current_value_as = None
        self._custom_function = custom_function
        self.characteristic_value = characteristic_value
        self.sp_mirrors_rbv = sp_mirrors_rbv

    def __repr__(self):
        return "{} '{}': sp={}, sp_rbv={}, rbv={}, changed={}".format(
            __name__, self.name, self._set_point, self._set_point_rbv, self.rbv, self.sp_changed
        )

    def _add_to_parameter_groups(self):
        """
        Add this parameter to relevant parameter groups (for display purposes).
        """
        self.group_names = [BeamlineParameterGroup.ALL]

    @abc.abstractmethod
    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccessful.
        Subclassed to handle type casting.
        """

    @abc.abstractmethod
    def _initialise_sp_from_motor(self, _):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """

    def _set_initial_sp(self, sp_init):
        """
        Populate the setpoint and setpoint readback with a value and trigger relevant listeners.

        Args:
            sp_init: The setpoint value to set
        """
        if self.read_only:
            self._set_point = self._rbv()
        else:
            self._set_point = sp_init
            self._set_point_rbv = sp_init
            self.trigger_listeners(
                ParameterInitUpdate(self._set_point, AlarmSeverity.No, AlarmStatus.No)
            )

    @property
    def rbv(self):
        """
        Returns: the read back value
        """
        return self._rbv()

    @property
    def rbv_at_sp(self):
        """
        Returns: Does the read back value match the set point target within a defined tolerance
        """
        if self.rbv is None or self._set_point_rbv is None:
            return False

        return abs(self.rbv - self._set_point_rbv) < self._rbv_to_sp_tolerance

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
        if not self.read_only:
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
    def sp(self, set_point):
        """
        Set the set point and move to it.
        Args:
            set_point: new set point
        """
        if not self.read_only:
            self._set_sp(set_point)

    def _set_sp_perform_no_move(self, value):
        """
        Set the set points as far down as the component layer but don't move the drivers
        Args:
            value: new value for setpoint
        """
        self._sp_no_move(value)
        self.move_to_sp_no_callback()

    def _set_sp(self, value):
        """
        Set the set point and move to do, private function needed for define position
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
        self.trigger_listeners(RequestMoveEvent(self))

    def move_to_sp_no_callback(self):
        """
        Move the component but don't call a callback indicating a move has been performed.
        """
        if self.sp_mirrors_rbv:
            self.sp_no_move = self._rbv()
        original_set_point_rbv = self._set_point_rbv
        self._set_point_rbv = self._set_point
        if self._sp_is_changed:
            logger.info("New value set for parameter {}: {}".format(self.name, self._set_point_rbv))
        try:
            self._check_and_move_component()
        except Exception:
            self._set_point_rbv = original_set_point_rbv
            raise

        if self._custom_function is not None:
            CUSTOM_FUNCTION_POOL.submit(
                self._run_custom_function, self._set_point_rbv, original_set_point_rbv
            )

        self._sp_is_changed = False
        if self._autosave:
            param_float_autosave.write_parameter(self._name, self._set_point_rbv)
        self._on_update_sp_rbv()

    def _run_custom_function(self, new_sp, original_sp):
        """
        Run the users custom function attached to this parameter
        Args:
            new_sp: the setpoint that has just been set
            original_sp: the value of the setpoint before the move was called
        """
        logger.debug(f"Running custom function on parameter {self.name} ...")
        try:
            message = self._custom_function(new_sp, original_sp)
            logger.debug(
                f"... Finished running custom function on parameter {self.name} it returned: {message}"
            )
            if message is not None:
                STATUS_MANAGER.update_error_log(
                    f"Custom function on parameter {self.name} returned: {message}"
                )
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo(
                        f"Custom function returned: {message}", self.name, Severity.NO_ALARM
                    )
                )
        except Exception as ex:
            STATUS_MANAGER.update_error_log(
                f"Custom function on parameter {self.name} failed with {ex}"
            )
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Custom function on parameter failed.", self.name, Severity.MAJOR_ALARM)
            )

    def move_to_sp_rbv_no_callback(self):
        """
        Repeat the move to the last set point.
        """
        self._check_and_move_component()

    def _on_update_rbv(self, _):
        """
        Trigger all rbv listeners

        Args:
            _: source of change which is not used
        """
        rbv = self._rbv()
        self._update_alarms()
        self.trigger_listeners(ParameterReadbackUpdate(rbv, self.alarm_severity, self.alarm_status))
        self.trigger_listeners(ParameterAtSetpointUpdate(self.rbv_at_sp))

    def _update_alarms(self):
        """
        To be implemented in subclass
        """
        alarm_info = self._get_alarm_info()
        if alarm_info is not None:
            self.alarm_severity = alarm_info[0]
            self.alarm_status = alarm_info[1]

    def _get_alarm_info(self):
        """
        To be implemented in subclass
        """
        raise NotImplementedError()

    @property
    def is_changing(self):
        """
        Returns: Is the parameter changing (rotating, displacing etc.)
        """
        raise NotImplementedError()

    def _on_update_changing_state(self, _: Optional[AxisChangingUpdate]):
        """
        Runs all the current listeners on the changing state because something has changed.

        Args:
            _: The update event
        """
        self.trigger_listeners(ParameterChangingUpdate(self.is_changing))

    def _on_update_sp_rbv(self):
        """
        Trigger all sp rbv listeners
        """
        self.trigger_listeners(
            ParameterSetpointReadbackUpdate(self._set_point_rbv, AlarmSeverity.No, AlarmStatus.No)
        )
        self.trigger_listeners(ParameterAtSetpointUpdate(self.rbv_at_sp))

    @property
    def name(self):
        """
        Returns:
            (str): name of this beamline parameter
        """
        return self._name

    @property
    def sp_changed(self):
        """
        Returns: Has set point been changed since the last move
        """
        return self._sp_is_changed if not self.read_only else False

    def _check_and_move_component(self):
        """
        Checks whether this parameter is initialised and moves the underlying component to its setpoint if so.
        """
        if self._set_point_rbv is not None:
            self._move_component()
        else:
            STATUS_MANAGER.update_active_problems(
                ProblemInfo(
                    "No parameter initialization value found", self.name, Severity.MAJOR_ALARM
                )
            )
            raise ParameterNotInitializedException(self.name)

    @abc.abstractmethod
    def _move_component(self):
        """
        Moves the component(s) associated with this parameter to the setpoint.
        """

    @abc.abstractmethod
    def _rbv(self):
        """
        Returns: the read back value
        """

    @abc.abstractmethod
    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """

    def _log_autosave_type_error(self):
        """
        Logs an error that the autosave value this parameter was trying to read was of the wrong type.
        """
        STATUS_MANAGER.update_error_log(
            "Could not read autosave value for parameter {}: unexpected type.".format(self.name)
        )
        STATUS_MANAGER.update_active_problems(
            ProblemInfo(
                "Parameter autosave value has unexpected type", self.name, Severity.MINOR_ALARM
            )
        )

    def _trigger_listeners_disabled(self):
        value = self.is_disabled or self.is_locked or self.read_only
        self.trigger_listeners(ParameterDisabledUpdate(value))

    @property
    def is_disabled(self):
        """
        Returns: Whether this parameter is currently active (i.e. settable)
        """
        return self._is_disabled

    @is_disabled.setter
    def is_disabled(self, value: bool):
        """
        Args:
             value: Whether this parameter is currently active (i.e. settable)
        """
        self._is_disabled = value
        self._trigger_listeners_disabled()

    @property
    def is_locked(self):
        """
        Returns: Whether this parameter is currently locked (i.e. settable)
        """
        return self._is_locked

    @is_locked.setter
    def is_locked(self, value: bool):
        """
        Args:
             value: Whether this parameter is currently locked (i.e. settable)
        """
        self._is_locked = value
        self._trigger_listeners_disabled()


class VirtualParameter(BeamlineParameter):
    def __init__(self, name: str, engineering_unit: str, description: str = None):
        super(VirtualParameter, self).__init__(name, description=description, autosave=True)
        self.engineering_unit = engineering_unit

        self._initialise_sp_from_file()

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        self.group_names.append(BeamlineParameterGroup.MISC)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccessful.
        """
        sp_init = param_float_autosave.read_parameter(self._name, None)
        if sp_init is not None:
            self._set_initial_sp(sp_init)
        else:
            self._set_initial_sp(0)

    def _initialise_sp_from_motor(self, _):
        """
        This parameter is not tied to a real motor
        """
        pass

    def _move_component(self):
        """
        Does not have any component so do not move
        """
        pass

    def _rbv(self):
        return self._set_point_rbv

    def validate(self, drivers):
        return []


class AxisParameter(BeamlineParameter):
    """
    Beamline Parameter that reads and write values on an axis of a component.
    """

    def __init__(
        self,
        name: str,
        component: "Component",
        axis: ChangeAxis,
        description: str = None,
        autosave: bool = False,
        rbv_to_sp_tolerance: float = 0.002,
        custom_function: Optional[Callable[[Any, Any], str]] = None,
        characteristic_value="",
        sp_mirrors_rbv=False,
    ):
        """
        Initialiser.
        Args:
            name:  name of the parameter. Parameter will have a this PV in upper case
            component: component for this parameter
            axis: the axis of the component
            description: Description of the parameter; if None defaults to the name of the parameter
            autosave: True to autosave this parameter when its value is moved to; False don't
            rbv_to_sp_tolerance: an error is reported if the difference between the read back value and setpoint
                is larger than this value
            custom_function: custom function to run on move
            characteristic_value: PV which the user wants to group with this parameter; leave out for no value.
                This should not include the instrument prefix, e.g. MOT:MTR0101
            sp_mirrors_rbv: if True the sp gets set to the readback value when this parameter is asked to perform a
                move; False this doesn't happen
        """
        self.component = component
        self.axis = axis
        if description is None:
            description = name
        super(AxisParameter, self).__init__(
            name,
            description,
            autosave,
            rbv_to_sp_tolerance=rbv_to_sp_tolerance,
            custom_function=custom_function,
            characteristic_value=characteristic_value,
            sp_mirrors_rbv=sp_mirrors_rbv,
        )

        if axis in [
            ChangeAxis.ANGLE,
            ChangeAxis.PHI,
            ChangeAxis.PSI,
            ChangeAxis.CHI,
            ChangeAxis.DISPLACEMENT_ANGLE,
        ]:
            self.engineering_unit = "deg"
        else:
            self.engineering_unit = "mm"

        if axis in [ChangeAxis.DISPLACEMENT_POSITION, ChangeAxis.DISPLACEMENT_ANGLE]:
            self.read_only = True
            self._trigger_listeners_disabled()
            self.component.beam_path_set_point.axis[self.axis].add_listener(
                SetRelativeToBeamUpdate, self._update_sp_from_component
            )

        self._initialise_setpoint()
        self._initialise_beam_path_sp_listeners()
        self._initialise_beam_path_rbv_listeners()

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        if self.axis in [ChangeAxis.POSITION, ChangeAxis.ANGLE]:
            self.group_names.append(BeamlineParameterGroup.COLLIMATION_PLANE)
        else:
            self.group_names.append(BeamlineParameterGroup.MISC)

    def _update_sp_from_component(self, update: SetRelativeToBeamUpdate):
        new_sp = update.relative_to_beam
        self._sp_no_move(new_sp)
        self._set_point_rbv = new_sp  # can not be applied by move

    def _initialise_setpoint(self):
        """
        Initialise the setpoint value for this parameter.
        """
        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self.component.beam_path_set_point.axis[self.axis].add_listener(
                InitUpdate, self._initialise_sp_from_motor
            )
            self.component.beam_path_set_point.in_beam_manager.add_listener(
                InitUpdate, self._initialise_sp_from_motor
            )

    def _initialise_beam_path_sp_listeners(self):
        """
        Add listeners to the setpoint beam path calc.
        """
        self.component.beam_path_set_point.in_beam_manager.add_listener(
            ComponentInBeamUpdate, self._on_update_in_beam_state, run_listener=True
        )

    def _initialise_beam_path_rbv_listeners(self):
        """
        Add listeners to the readback beam path calc.
        """
        self.component.beam_path_rbv.add_listener(BeamPathUpdate, self._on_update_rbv)
        rbv_axis = self.component.beam_path_rbv.axis[self.axis]
        rbv_axis.add_listener(AxisChangingUpdate, self._on_update_changing_state)
        rbv_axis.add_listener(PhysicalMoveUpdate, self._on_update_rbv)

        if rbv_axis.can_define_axis_position_as:
            self.define_current_value_as = DefineCurrentValueAsParameter(
                rbv_axis.define_axis_position_as, self._set_sp_perform_no_move, self
            )

    def _on_update_in_beam_state(self, update: ComponentInBeamUpdate):
        """
        Trigger an update on this parameters is-disabled state after a change in the component's in-beam status.

        Args:
            update: The update event
        """
        self.is_disabled = self.sp_mirrors_rbv or not update.value

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccessful.
        """
        sp_init = param_float_autosave.read_parameter(self._name, None)
        if sp_init is not None:
            self._set_initial_sp(sp_init)
            self.component.beam_path_set_point.axis[self.axis].autosaved_value = sp_init
            self._move_component()

    def _initialise_sp_from_motor(self, _):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        if not self.component.beam_path_set_point.in_beam_manager.get_is_in_beam():
            autosave_val = self.component.beam_path_set_point.axis[self.axis].autosaved_value
            if autosave_val is not None:
                init_sp = autosave_val
            else:
                # If the axis is out of the beam and there is not autosave the displacement should be set to 0
                init_sp = 0.0
                STATUS_MANAGER.update_error_log(
                    "Parameter {} is parkable so should have an autosave value but "
                    "doesn't. Has been set to 0 check its value".format(self.name)
                )
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Parameter has no autosave value", self.name, Severity.MINOR_ALARM)
                )
            self.component.beam_path_set_point.axis[self.axis].set_relative_to_beam(init_sp)
        else:
            init_sp = self.component.beam_path_set_point.axis[self.axis].get_relative_to_beam()

        self._set_initial_sp(init_sp)

    def _move_component(self):
        self.component.beam_path_set_point.axis[self.axis].set_relative_to_beam(self._set_point_rbv)

    def _rbv(self):
        """
        Returns: readback value for the parameter, e.g. tracking displacement above the beam
        """
        return self.component.beam_path_rbv.axis[self.axis].get_relative_to_beam()

    @property
    def rbv_at_sp(self):
        """
        Returns: Does the read back value match the set point target within a defined tolerance, only if the component
        is in the beam
        """
        if self.rbv is None or self._set_point_rbv is None:
            return False

        return (
            not self.component.beam_path_set_point.axis[self.axis].is_in_beam
            or abs(self.rbv - self._set_point_rbv) < self._rbv_to_sp_tolerance
        )

    def _get_alarm_info(self):
        """
        Returns the alarm information for the axis of this component.
        """
        return self.component.beam_path_rbv.axis[self.axis].alarm

    @property
    def is_changing(self):
        """
        Returns: Is the parameter changing (e.g. rotating or displacing)
        """
        return self.component.beam_path_rbv.axis[self.axis].is_changing

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """
        return []


class InBeamParameter(BeamlineParameter):
    """
    Parameter which sets whether a given device is in the beam.
    """

    def __init__(
        self,
        name: str,
        component: "Component",
        description: str = None,
        autosave: bool = False,
        custom_function: Optional[Callable[[bool, bool], str]] = None,
    ):
        """
        Initializer.
        Args:
            name: Name of the in-beam parameter
            component: the component to be moved in or out of the beam
            autosave: True if the parameter should be autosaved on change and read on start; False otherwise
            description: description
            custom_function: custom function to run on move
        """
        if description is None:
            description = "{} component is in the beam".format(name)
        super(InBeamParameter, self).__init__(
            name, description, autosave, rbv_to_sp_tolerance=0.001, custom_function=custom_function
        )
        self._component = component

        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._component.beam_path_set_point.in_beam_manager.add_listener(
                InitUpdate, self._initialise_sp_from_motor
            )
        self._component.beam_path_rbv.add_listener(BeamPathUpdate, self._on_update_rbv)
        self._component.beam_path_rbv.in_beam_manager.add_listener(
            AxisChangingUpdate, self._on_update_changing_state
        )

        self.parameter_type = BeamlineParameterType.IN_OUT

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        self.group_names.append(BeamlineParameterGroup.TOGGLE)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccessful.
        """
        sp_init = param_bool_autosave.read_parameter(self._name, None)
        if sp_init is not None:
            self._set_initial_sp(sp_init)
            self._component.beam_path_set_point.initialise_is_in_beam_from_file(self._set_point_rbv)

    def _initialise_sp_from_motor(self, _):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        init_sp = self._component.beam_path_set_point.is_in_beam
        self._set_initial_sp(init_sp)

    def _move_component(self):
        self._component.beam_path_set_point.is_in_beam = self._set_point_rbv

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors
        """

        errors = []
        for driver in drivers:
            if driver.is_for_component(self._component):
                if driver.has_out_of_beam_position():
                    break
        else:
            errors.append(
                "No driver found with out of beam position for component {}".format(
                    self._component.name
                )
            )
        return errors

    def _rbv(self):
        return self._component.beam_path_rbv.is_in_beam

    def _get_alarm_info(self):
        """
        Returns the alarm information for the displacement axis of this component.
        """
        return self._component.beam_path_rbv.in_beam_manager.alarm

    @property
    def is_changing(self):
        """
        Returns: Is the parameter changing (rotating, displacing etc.)
        """
        return self._component.beam_path_rbv.in_beam_manager.is_changing


class DirectParameter(BeamlineParameter):
    """
    Parameter which is not linked to the beamline component layer but hooks directly into a motor axis. This parameter
    is just a wrapper to present a motor PV as a reflectometry style PV and does not track the beam path.
    """

    def __init__(
        self,
        name: str,
        pv_wrapper: PVWrapper,
        description: str = None,
        autosave: bool = False,
        rbv_to_sp_tolerance: float = DEFAULT_RBV_TO_SP_TOLERANCE,
        custom_function: Optional[Callable[[Any, Any], str]] = None,
        engineering_correction: "EngineeringCorrection" = None,
    ):
        """
        Args:
            name: The name of the parameter
            pv_wrapper: The pv wrapper this parameter talks to
            description: The description
            autosave: Whether the setpoint for this parameter should be autosaved
            rbv_to_sp_tolerance: The max difference between setpoint and readback value for considering the
                parameter to be "at readback value"
            custom_function: custom function to run on move
        """
        # This is to avoid circular imports when instantiating NoCorrection()
        from ReflectometryServer.engineering_corrections import NoCorrection

        self.engineering_correction = (
            engineering_correction if engineering_correction is not None else NoCorrection()
        )
        self._pv_wrapper = pv_wrapper
        super(DirectParameter, self).__init__(
            name,
            description,
            autosave,
            rbv_to_sp_tolerance=rbv_to_sp_tolerance,
            custom_function=custom_function,
        )
        self._last_update = None

        self._pv_wrapper.add_listener(ReadbackUpdate, self._cache_and_update_rbv)
        self._pv_wrapper.add_listener(IsChangingUpdate, self._on_is_changing_change)
        self._pv_wrapper.initialise()

        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._initialise_sp_from_motor(None)

        self._no_move_because_is_define = False
        self.define_current_value_as = DefineCurrentValueAsParameter(
            self._pv_wrapper.define_position_as, self._set_sp_perform_no_move, self
        )

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        self.group_names.append(BeamlineParameterGroup.SLIT)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccessful.
        """
        sp_init = param_float_autosave.read_parameter(self._name, None)
        if sp_init is not None:
            self._set_initial_sp(self.engineering_correction.to_axis(sp_init))

    def _initialise_sp_from_motor(self, _):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        self._set_initial_sp(self.engineering_correction.to_axis(self._pv_wrapper.sp))

    def _cache_and_update_rbv(self, update):
        """
        Update the readback value.

        Args:
            update (ReflectometryServer.pv_wrapper.ReadbackUpdate): update of the readback value of the axis
        """
        self._last_update = update
        self._on_update_rbv(self)

    def _move_component(self):
        if not self._no_move_because_is_define and not self.rbv_at_sp:
            self._pv_wrapper.sp = self.engineering_correction.to_axis(self._set_point_rbv)

    def _set_sp_perform_no_move(self, new_value):
        """
        This is a work around because this does not have a component. See ticket 4902
        When stripping out get rid of _no_move_because_is_define
        Args:
            new_value: the new value for the setpoint
        """
        try:
            self._no_move_because_is_define = True
            self._set_sp(self.engineering_correction.to_axis(new_value))
        finally:
            self._no_move_because_is_define = False

    def _rbv(self):
        return self.engineering_correction.from_axis(self._last_update.value, self.sp)

    def _get_alarm_info(self):
        """
        Returns the alarm information for this slit gap parameter.
        """
        return self._last_update.alarm_severity, self._last_update.alarm_status

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """
        return []

    def _on_is_changing_change(self, _):
        """
        Trigger an update for the is_changing status of this parameter on such an event in the PV wrapper.

        Args:
            _ (ReflectometryServer.pv_wrapper.IsChangingUpdate): The update event
        """
        self._on_update_changing_state(None)

    @property
    def is_changing(self):
        """
        Returns: Is the parameter changing (displacing)
        """
        return self._pv_wrapper.is_moving


class SlitGapParameter(DirectParameter):
    """
    Parameter which sets the gap on a slit.
    """

    def __init__(
        self,
        name: str,
        pv_wrapper: JawsAxisPVWrapper,
        description: str = None,
        autosave: bool = False,
        rbv_to_sp_tolerance: float = 0.002,
        custom_function: Optional[Callable[[Any, Any], str]] = None,
    ):
        """
        Args:
            name: The name of the parameter
            pv_wrapper: The pv wrapper this parameter talks to
            description: The description
            autosave: Whether the setpoint for this parameter should be autosaved
            rbv_to_sp_tolerance: The max difference between setpoint and readback value for considering the
                parameter to be "at readback value"
            custom_function: custom function to run on move
        """
        super(SlitGapParameter, self).__init__(
            name,
            pv_wrapper,
            description,
            autosave,
            rbv_to_sp_tolerance=rbv_to_sp_tolerance,
            custom_function=custom_function,
        )
        self.engineering_unit = "mm"

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        if self._pv_wrapper.is_vertical:
            self.group_names.append(BeamlineParameterGroup.FOOTPRINT_PARAMETER)


class EnumParameter(BeamlineParameter):
    """
    Beamline parameter with a number of options that can be selected. The readback is the same as the setpoint readback
    and get set as soon as a move occurs.
    """

    def __init__(
        self,
        name: str,
        options: List[str],
        description: Optional[str] = None,
        custom_function: Optional[Callable[[Any, Any], str]] = None,
    ):
        """
        Initializer.
        NB parameter is always autosaved
        Args:
            name: name of the parameter
            options: a list of string options allowed
            description: description of the parameter
            custom_function: custom function to run on move
        """
        super(EnumParameter, self).__init__(
            name, description=description, autosave=True, custom_function=custom_function
        )
        self.parameter_type = BeamlineParameterType.ENUM
        self.options = options
        if self._autosave:
            self._initialise_sp_from_file()

    def _add_to_parameter_groups(self):
        super()._add_to_parameter_groups()
        self.group_names.append(BeamlineParameterGroup.TOGGLE)

    def validate(self, drivers: List["IocDriver"]) -> List[str]:
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers: list of driver to help with validation

        Returns:
            list of problems; Empty list if there are no errors

        """
        errors = []
        if len(self.options) < 1:
            errors.append("There are no options set for parameter {}".format(self.name))
        if len(self.options) != len(set(self.options)):
            errors.append("There are duplicate options for parameter {}".format(self.name))
        return errors

    def _on_update_sp_rbv(self):
        """
        Trigger all set point rbv listeners. Also because it set the rbv trigger those listeners.
        """
        super(EnumParameter, self)._on_update_sp_rbv()
        self._on_update_rbv(self)

    def _rbv(self):
        return self.sp_rbv

    def _initialise_sp_from_file(self):
        try:
            sp_init = param_string_autosave.read_parameter(self._name, self.options[0])
            self._set_initial_sp(sp_init)
        except IndexError:
            STATUS_MANAGER.update_error_log(
                "No options for optional parameter, {}".format(self.name)
            )

    def _initialise_sp_from_motor(self, _):
        # Optional parameters should always be autosaved and should not be initialised from the motor there is no code
        # to perform this operation so this is a major error if triggered.
        STATUS_MANAGER.update_error_log(
            "Optional parameter, {}, was asked up init from motor".format(self.name)
        )
        STATUS_MANAGER.update_active_problems(
            ProblemInfo("Optional Parameter updating from motor", self.name, Severity.MAJOR_ALARM)
        )

    def _move_component(self):
        if self.sp_rbv not in self.options:
            raise ValueError("Invalid option: {}".format(self.sp_rbv))

    @property
    def rbv_at_sp(self) -> bool:
        """
        Returns: Does the read back value match the set point target within a defined tolerance
        """
        return True

    def _get_alarm_info(self):
        return AlarmSeverity.No, AlarmStatus.No
