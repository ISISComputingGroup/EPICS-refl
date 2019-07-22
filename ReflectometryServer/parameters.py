"""
Parameters that the user would interact with
"""
from file_io import AutosaveType, read_autosave_value, write_autosave_value
import logging

from enum import Enum
from server_common.utilities import print_and_log, SEVERITY

logger = logging.getLogger(__name__)


class ParameterNotInitializedException(Exception):
    def __init__(self, err):
        self.message = str(err)

    def __str__(self):
        return self.message


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
    FOOTPRINT_PARAMETER = 2
    GAP_VERTICAL = 3
    GAP_HORIZONTAL = 4


class BeamlineParameter(object):
    """
    General beamline parameter that can be set. Subclass must implement _move_component to decide what to do with the
    value that is set.
    """
    def __init__(self, name, sim=False, init=None, description=None, autosave=False, rbv_tolerance=0.04):
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
        self._autosave = autosave
        self.group_names = []
        self._rbv_change_listeners = set()
        self._sp_rbv_change_listeners = set()
        self._after_moving_state_update_listeners = set()
        self._after_at_position_listeners = set()
        self._init_listeners = set()
        self.rbv_tolerance = rbv_tolerance
        #self._in_mode = init

    def __repr__(self):
        return "{} '{}': sp={}, sp_rbv={}, rbv={}, changed={}".format(__name__, self.name, self._set_point,
                                                                      self._set_point_rbv, self.rbv, self.sp_changed)# self.in_mode)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccesful.
        Subclassed to handle type casting.
        """
        raise NotImplemented("This must be implemented in the subclass.")

    def _initialise_sp_from_motor(self):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        raise NotImplemented("This must be implemented in the subclass.")

    def _set_initial_sp(self, sp_init):
        """
        Populate the setpoint and setpoint readback with a value and trigger relevant listeners.

        Params:
            sp_init: The setpoint value to set
        """
        self._set_point = sp_init
        self._set_point_rbv = sp_init
        self._trigger_init_listeners()

    @property
    def rbv(self):
        """
        Returns: the read back value
        """
        return self._rbv()

    @property
    def rbv_at_position(self):
        if abs(self.rbv - self._set_point_rbv) > self.rbv_tolerance:
            print("PARAM:@Property:rbv_at_position:{}:FALSE ({:0.3f})".format(self.name, abs(self.rbv - self._set_point_rbv)))
            return False
        else:
            #print("PARAM:@Property:rbv_at_position:{}:true ({:0.3f})".format(self.name, abs(self.rbv - self._set_point_rbv)))
            return True

    @property
    def sp_rbv(self):
        """
        Returns: the set point read back value, i.e. wherethe last move was instructed to go
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
        self._check_and_move_component()
        self._sp_is_changed = False
        if self._autosave:
            write_autosave_value(self._name, self._set_point_rbv, AutosaveType.PARAM)
        self._trigger_sp_rbv_listeners(self)

    def move_to_sp_rbv_no_callback(self):
        """
        Repeat the move to the last set point.
        """
        self._check_and_move_component()

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
    def is_changing(self):
        raise NotImplemented()

    def add_after_moving_state_update_listener(self, listener):
        """
        """
        self._after_moving_state_update_listeners.add(listener)

    def _trigger_after_moving_state_update(self):
        """
        """
        print("PARAM:_trigger_after_moving_state_update:{}".format(self.is_changing))
        for listener in self._after_moving_state_update_listeners:
            listener(self.is_changing)

    def add_after_rbv_at_position_listener(self, listener):
        """
        """
        print("PARAM:add_after_rbv_at_position:{}".format(listener))
        self._after_at_position_listeners.add(listener)

    def _trigger_after_rbv_at_position_update(self):
        """
        """
        print("---- PARA: triggering after_at_position listeners")
        print("PARAM:_trigger_after_rbv_at_position_update:{}".format(self.rbv_at_position))
        for listener in self._after_at_position_listeners:
            print("PARAM:_trigger_after_rbv_at_position_update:{}".format(listener))
            listener(self.rbv_at_position)
        print("----------")

    def add_sp_rbv_change_listener(self, listener):
        """
        Add a listener which should be called if the rbv value changes.
        Args:
            listener: the function to call with one argument which is the new rbv value
        """
        self._sp_rbv_change_listeners.add(listener)

    def _trigger_sp_rbv_listeners(self, source):
        """
        Trigger all rbv listeners

        Args:
            source: source of change which is not used
        """
        for listener in self._sp_rbv_change_listeners:
            listener(self._set_point_rbv)

    def add_init_listener(self, listener):
        self._init_listeners.add(listener)

    def _trigger_init_listeners(self):
        for listener in self._init_listeners:
            listener(self._set_point)

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

    def _check_and_move_component(self):
        """
        Checks whether this parameter is initialised and moves the underlying component to its setpoint if so.
        """
        if self._set_point_rbv is not None:
            self._move_component()
        else:
            raise ParameterNotInitializedException(self.name)

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

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """
        raise NotImplemented("This must be implemented in the sub class")

    def _log_autosave_type_error(self):
        """
        Logs an error that the autosave value this parameter was trying to read was of the wrong type.
        """
        logger.error("Could not read autosave value for parameter {}: unexpected type.".format(self.name))


class AngleParameter(BeamlineParameter):
    """
    The angle of the component measured from the incoming beam, this could be theta, or the supermirror angle or
        title jaws angle.
    Angle is measure with +ve in the anti-clockwise direction)
    """

    def __init__(self, name, reflection_component, sim=False, init=0, description=None, autosave=False):
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
        super(AngleParameter, self).__init__(name, sim, init, description, autosave)
        self._reflection_component = reflection_component

        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._reflection_component.beam_path_set_point.add_init_listener(self._initialise_sp_from_motor)

        self._reflection_component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)
        self._reflection_component.beam_path_rbv.add_after_moving_state_update_listener(self._trigger_after_moving_state_update)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccesful.
        """
        sp_init = read_autosave_value(self._name, AutosaveType.PARAM)
        if sp_init is not None:
            try:
                angle = float(sp_init)
                self._set_initial_sp(angle)
                self._move_component()
            except ValueError as e:
                self._log_autosave_type_error()

    def _initialise_sp_from_motor(self):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        init_sp = self._reflection_component.beam_path_set_point.angle
        self._set_initial_sp(init_sp)

    def _move_component(self):
        self._reflection_component.beam_path_set_point.set_angle_relative_to_beam(self._set_point_rbv)

    def _rbv(self):
        return self._reflection_component.beam_path_rbv.get_angle_relative_to_beam()

    @property
    def is_changing(self):
        return self._reflection_component.beam_path_rbv.is_rotating

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """
        return []


class TrackingPosition(BeamlineParameter):
    """
    Component which tracks the position of the beam with a single degree of freedom. E.g. slit set on a height stage
    """

    def __init__(self, name, component, sim=False, init=0, description=None, autosave=False):
        """

        Args:
            name: Name of the variable
            component (ReflectometryServer.components.Component): component that the tracking is based on
            description (str): description
        """
        if description is None:
            description = "{} tracking position".format(name)
        super(TrackingPosition, self).__init__(name, sim, init, description, autosave)
        self._component = component

        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._component.beam_path_set_point.add_init_listener(self._initialise_sp_from_motor)

        self._component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)
        self._component.beam_path_rbv.add_after_moving_state_update_listener(self._trigger_after_moving_state_update)

        self.group_names.append(BeamlineParameterGroup.TRACKING)

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccesful.
        """
        sp_init = read_autosave_value(self._name, AutosaveType.PARAM)
        if sp_init is not None:
            try:
                sp_init = float(sp_init)
                self._set_initial_sp(sp_init)
                self._component.beam_path_set_point.autosaved_offset = sp_init
                self._move_component()
            except ValueError as e:
                self._log_autosave_type_error()

    def _initialise_sp_from_motor(self):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        if self._component.beam_path_set_point.is_in_beam:
            init_sp = self._component.beam_path_set_point.get_position_relative_to_beam()
        else:
            init_sp = 0.0
        self._set_initial_sp(init_sp)

    def _move_component(self):
        self._component.beam_path_set_point.set_position_relative_to_beam(self._set_point_rbv)

    def _rbv(self):
        """
        Returns: readback value for the tracking displacement above the beam
        """
        return self._component.beam_path_rbv.get_position_relative_to_beam()

    @property
    def is_changing(self):
        return self._component.beam_path_rbv.is_displacing

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

    def __init__(self, name, component, sim=False, init=False, description=None, autosave=False):
        """
        Initializer.
        Args:
            name (str): Name of the enabled parameter
            component (ReflectometryServer.components.Component): the component to be enabled or disabled
            description (str): description
        """
        if description is None:
            description = "{} component is in the beam".format(name)
        super(InBeamParameter, self).__init__(name, sim, init, description, autosave)
        self._component = component

        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._component.beam_path_set_point.add_init_listener(self._initialise_sp_from_motor)
        self._component.beam_path_rbv.add_after_beam_path_update_listener(self._trigger_rbv_listeners)

        self.parameter_type = BeamlineParameterType.IN_OUT

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccesful.
        """
        sp_init = read_autosave_value(self._name, AutosaveType.PARAM)
        if sp_init == "True":
            self._set_initial_sp(True)
            self._move_component()
        elif sp_init == "False":
            self._set_initial_sp(False)
            self._move_component()
        elif sp_init is not None:
            self._log_autosave_type_error()

    def _initialise_sp_from_motor(self):
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
                try:
                    if driver.has_out_of_beam_position():
                        break
                except AttributeError:
                    pass  # this is not a displacement driver so can not have this
        else:
            errors.append("No driver found with out of beam position for component {}".format(self.name))
        return errors

    def _rbv(self):
        return self._component.beam_path_rbv.is_in_beam

    @property
    def is_changing(self):
        if self._component.beam_path_rbv.is_displacing or self._component.beam_path_rbv.is_rotating:
            return True
        else:
            return False


class SlitGapParameter(BeamlineParameter):
    """
    Parameter which sets the gap on a slit. This differs from other beamline parameters in that it is not linked to the
    beamline component layer but hooks directly into a motor axis.
    """
    def __init__(self, name, pv_wrapper, sim=False, init=0, description=None, autosave=False):
        """
        Args:
            name (str): The name of the parameter
            pv_wrapper (ReflectometryServer.pv_wrapper._JawsAxisPVWrapper): The jaws pv wrapper this parameter talks to
            sim (bool): Whether it is a simulated parameter
            init (float): Initialisation value if simulated
            description (str): The description
        """
        super(SlitGapParameter, self).__init__(name, sim, init, description, autosave)
        self._pv_wrapper = pv_wrapper
        self._pv_wrapper.add_after_rbv_change_listener(self.update_rbv)
        self._pv_wrapper.add_after_is_changing_change_listener(self._on_moving_state_update)
        self._pv_wrapper.initialise()
        if pv_wrapper.is_vertical:
            self.group_names.append(BeamlineParameterGroup.FOOTPRINT_PARAMETER)
            self.group_names.append(BeamlineParameterGroup.GAP_VERTICAL)
        else:
            self.group_names.append(BeamlineParameterGroup.GAP_HORIZONTAL)


        if self._autosave:
            self._initialise_sp_from_file()
        if self._set_point_rbv is None:
            self._initialise_sp_from_motor()

    def _initialise_sp_from_file(self):
        """
        Read an autosaved setpoint for this parameter from the autosave file. Remains None if unsuccesful.
        """
        sp_init = read_autosave_value(self._name, AutosaveType.PARAM)
        if sp_init is not None:
            try:
                self._set_initial_sp(float(sp_init))
            except ValueError as e:
                self._log_autosave_type_error()

    def _initialise_sp_from_motor(self):
        """
        Get the setpoint value for this parameter based on the motor setpoint position.
        """
        self._set_initial_sp(self._pv_wrapper.sp)

    def update_rbv(self, new_value, alarm_severity, alarm_status):
        """
        Update the readback value.

        Args:
            new_value: new readback value that is given
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._rbv_value = new_value
        self._trigger_rbv_listeners(self)

    def _move_component(self):
        self._pv_wrapper.sp = self._set_point

    def _rbv(self):
        return self._rbv_value

    def validate(self, drivers):
        """
        Perform validation of this parameter returning a list of errors.

        Args:
            drivers (list[ReflectometryServer.ioc_driver.IocDriver]): list of driver to help with validation

        Returns:
            (list[str]): list of problems; Empty list if there are no errors

        """
        return []

    def _on_moving_state_update(self, new_value, alarm_severity, alarm_status):
        self._trigger_after_moving_state_update()

    @property
    def is_changing(self):
        return self._pv_wrapper.is_moving
