"""
Resources at a beamline level
"""
import logging
from collections import OrderedDict, namedtuple
from functools import partial
from enum import Enum
from pcaspy import Severity

from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.file_io import read_mode, save_mode
from ReflectometryServer.footprint_calc import BaseFootprintSetup
from ReflectometryServer.footprint_manager import FootprintManager
from ReflectometryServer.parameters import ParameterNotInitializedException

from server_common.channel_access import UnableToConnectToPVException

logger = logging.getLogger(__name__)


BeamlineStatus = namedtuple("Status", ['display_string', 'alarm_severity'])


class STATUS(Enum):
    """
    Beamline States.
    """
    OKAY = BeamlineStatus("OKAY", Severity.NO_ALARM)
    CONFIG_ERROR = BeamlineStatus("CONFIG_ERROR", Severity.MAJOR_ALARM)
    GENERAL_ERROR = BeamlineStatus("ERROR", Severity.MAJOR_ALARM)

    @property
    def display_string(self):
        """
        Returns: display string for the enum
        """
        return self.value.display_string

    @property
    def alarm_severity(self):
        """
        Returns: Alarm severity of beamline status
        """
        return self.value.alarm_severity


class BeamlineMode(object):
    """
    Beamline mode definition; which components and parameters are calculated on move.
    """

    def __init__(self, name, beamline_parameters_to_calculate, sp_inits=None, is_disabled=False):
        """
        Initialize.
        Args:
            name (str): name of the beam line mode
            beamline_parameters_to_calculate (list[str]): Beamline parameters in this mode
                which should be automatically moved to whenever a preceding parameter is changed
            sp_inits (dict[str, object]): The initial beamline parameter values that should be set when switching
                to this mode
            is_disabled (Boolean): True components allow input beamline to be changed; False they don't
        """
        self.name = name
        self._beamline_parameters_to_calculate = beamline_parameters_to_calculate
        if sp_inits is None:
            self._sp_inits = {}
        else:
            self._sp_inits = sp_inits
        self.is_disabled = is_disabled

    def has_beamline_parameter(self, beamline_parameter):
        """
        Args:
            beamline_parameter(ReflectometryServer.parameters.BeamlineParameter): the beamline parameter

        Returns: True if beamline_parameter is in this mode.
        """
        return beamline_parameter.name in self._beamline_parameters_to_calculate

    def get_parameters_in_mode(self, beamline_parameters, first_parameter=None):
        """
        Returns, in order, all those parameters which are in this mode. Starting with the parameter after the first
        parameter
        Args:
            beamline_parameters(list[ReflectometryServer.parameters.BeamlineParameter]): the beamline parameters which
                maybe in the mode
            first_parameter(ReflectometryServer.parameters.BeamlineParameter): the parameter after which to include
                parameters; None for include all

        Returns: a list of parameters after the first parameter which are in this mode

        """
        parameters_in_mode = []
        after_first = first_parameter is None
        for beamline_parameter in beamline_parameters:
            if beamline_parameter == first_parameter:
                after_first = True
            elif after_first and beamline_parameter.name in self._beamline_parameters_to_calculate:
                parameters_in_mode.append(beamline_parameter)
        return parameters_in_mode

    @property
    def initial_setpoints(self):
        """
        Set point initial values
        Returns: the set point

        """
        return self._sp_inits

    def validate(self, beamline_parameters):
        """
        Validate the parameters in the mode against beamline parameters.
        Args:
            beamline_parameters: the beamline parameters
        Returns:
            list of errors
        """
        errors = []
        for beamline_parameter in self._beamline_parameters_to_calculate:
            if beamline_parameter not in beamline_parameters:
                errors.append("Beamline parameter '{}' in mode '{}' not in beamline".format(
                    beamline_parameters, self.name))

        for sp_init in self._sp_inits.keys():
            if sp_init not in beamline_parameters:
                errors.append("SP Init '{}' in mode '{}' not in beamline".format(sp_init, self.name))

        return errors


class Beamline(object):
    """
    The collection of all beamline components.
    """

    def __init__(self, components, beamline_parameters, drivers, modes, incoming_beam=None,
                 footprint_setup=None):
        """
        The initializer.
        Args:
            components (list[ReflectometryServer.components.Component]): The collection of beamline components
            beamline_parameters (list[ReflectometryServer.parameters.BeamlineParameter]): a dictionary of parameters
                that characterise the beamline
            drivers(list[ReflectometryServer.ioc_driver.IocDriver]): a list of motor drivers linked to a component in
                the beamline
            modes(list[BeamlineMode])
            incoming_beam (ReflectometryServer.geometry.PositionAndAngle): the incoming beam point
                (defaults to position 0,0 and angle 0)
            footprint_setup (ReflectometryServer.BaseFootprintSetup.BaseFootprintSetup): the foot print setup
        """

        self._components = components
        self._beam_path_calcs_set_point = []
        self._beam_path_calcs_rbv = []
        self._beamline_parameters = OrderedDict()
        self._drivers = drivers
        self._status = STATUS.OKAY
        self._message = ""
        self._active_mode_change_listeners = set()
        self._status_change_listeners = set()
        footprint_setup = footprint_setup if footprint_setup is not None else BaseFootprintSetup()
        self.footprint_manager = FootprintManager(footprint_setup)

        for beamline_parameter in beamline_parameters:
            self._beamline_parameters[beamline_parameter.name] = beamline_parameter
            beamline_parameter.after_move_listener = self._move_for_single_beamline_parameters

        self._modes = OrderedDict()
        for mode in modes:
            self._modes[mode.name] = mode

        self._validate(beamline_parameters, modes)

        for component in components:
            self._beam_path_calcs_set_point.append(component.beam_path_set_point)
            self._beam_path_calcs_rbv.append(component.beam_path_rbv)
            component.beam_path_set_point.add_after_beam_path_update_on_init_listener(
                self.update_next_beam_component_on_init)
            component.beam_path_set_point.add_after_beam_path_update_listener(
                partial(self.update_next_beam_component, calc_path_list=self._beam_path_calcs_set_point))
            component.beam_path_rbv.add_after_beam_path_update_listener(
                partial(self.update_next_beam_component, calc_path_list=self._beam_path_calcs_rbv))

        self._incoming_beam = incoming_beam if incoming_beam is not None else PositionAndAngle(0, 0, 0)

        for driver in self._drivers:
            driver.initialise()

        self.update_next_beam_component(None, self._beam_path_calcs_rbv)
        self.update_next_beam_component(None, self._beam_path_calcs_set_point)

        self._initialise_mode(modes)

    def _validate(self, beamline_parameters, modes):
        errors = []

        beamline_parameters_names = [beamline_parameter.name for beamline_parameter in beamline_parameters]
        for name in beamline_parameters_names:
            if beamline_parameters_names.count(name) > 1:
                errors.append("Beamline parameters must be uniquely named. Duplicate '{}'".format(name))

        mode_names = [mode.name for mode in modes]
        for mode in mode_names:
            if mode_names.count(mode) > 1:
                errors.append("Mode must be uniquely named. Duplicate '{}'".format(mode))

        for mode in modes:
            errors.extend(mode.validate(self._beamline_parameters.keys()))

        for parameter in self._beamline_parameters.values():
            errors.extend(parameter.validate(self._drivers))

        if len(errors) > 0:
            logger.error("There is a problem with beamline configuration:\n    {}".format("\n    ".join(errors)))
            raise ValueError("Problem with beamline configuration: {}".format(";".join(errors)))

    @property
    def parameter_types(self):
        """
        Returns:
            dict[str, ReflectometryServer.parameters.BeamlineParameterType]: a dictionary of parameter type,
                keyed by their name
        """
        types = OrderedDict()
        for beamline_parameter in self._beamline_parameters.values():
            types[beamline_parameter.name] = (beamline_parameter.parameter_type, beamline_parameter.group_names,
                                              beamline_parameter.description)
        return types

    @property
    def mode_names(self):
        """
        Returns: the names of all the modes
        """
        return self._modes.keys()

    @property
    def active_mode(self):
        """
        Returns: the name of the current modes; None for no active mode
        """
        try:
            return self._active_mode.name
        except AttributeError:
            return None

    @active_mode.setter
    def active_mode(self, mode):
        """
        Set the current mode (setting presets as expected)
        Args:
            mode (str): name of the mode to set
        """
        try:
            self._active_mode = self._modes[mode]
            for component in self._components:
                component.set_incoming_beam_can_change(not self._active_mode.is_disabled)
            save_mode(mode)
            self._init_params_from_mode()
            self._trigger_active_mode_change()
        except KeyError:
            raise ValueError("Not a valid mode name: '{}'".format(mode))

    @property
    def move(self):
        """
        Move the beamline.
        Returns: 0
        """
        return 0

    @move.setter
    def move(self, _):
        """
        Move to all the beamline parameters in the mode or that have changed
        Args:
            _: dummy can be anything
        """
        self._move_for_all_beamline_parameters()

    def __getitem__(self, item):
        """
        Args:
            item: the index of the component

        Returns: the indexed component
        """
        return self._components[item]

    def get_param_names_in_mode(self):
        """ Returns a list of the name of params in the current mode.
        """

        param_names_in_mode = []
        parameters = self._beamline_parameters.values()
        for param in self._active_mode.get_parameters_in_mode(parameters):
            param_names_in_mode.append(param.name)
        return param_names_in_mode

    def update_next_beam_component(self, source_component, calc_path_list):
        """
        Updates the next component in the beamline.
        Args:
            source_component(None|ReflectometryServer.beam_path_calc.TrackingBeamPathCalc): source component of the
                update or None for not from component change
            calc_path_list(List[ReflectometryServer.components.BeamPathCalc]): list of beam calcs order in the same
                order as components
        """
        if source_component is None:
            outgoing = self._incoming_beam
            comp_index = -1
        else:
            outgoing = source_component.get_outgoing_beam()
            comp_index = calc_path_list.index(source_component)

        try:
            calc_path_list[comp_index + 1].set_incoming_beam(outgoing)
        except IndexError:
            pass  # no more components to update

    def update_next_beam_component_on_init(self, source_component):
        """
        Updates the next component in the beamline after an initialisation event, recalculating the setpoint beam path
        while preserving autosaved values.

        Args:
            source_component(None|ReflectometryServer.beam_path_calc.TrackingBeamPathCalc): source component of the
                update or None for not from component change
        """
        if source_component is None:
            outgoing = self._incoming_beam
            comp_index = -1
        else:
            outgoing = source_component.get_outgoing_beam()
            comp_index = self._beam_path_calcs_set_point.index(source_component)

        try:
            next_component = self._beam_path_calcs_set_point[comp_index + 1]
            next_component.set_incoming_beam(outgoing, on_init=True)
        except IndexError:
            pass  # no more components to update

    def _move_for_all_beamline_parameters(self):
        """
        Updates the beamline parameters to the latest set point value; reapplies if they are in the mode. Then moves to
        latest postions.
        """
        parameters = self._beamline_parameters.values()
        parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, None)

        for beamline_parameter in parameters:
            if beamline_parameter in parameters_in_mode or beamline_parameter.sp_changed:
                try:
                    beamline_parameter.move_to_sp_no_callback()
                except ParameterNotInitializedException as e:
                    self.set_status(STATUS.GENERAL_ERROR,
                                    "Parameter {} has not been initialized. Check reflectometry configuration is "
                                    "correct and underlying motor IOC is running.".format(e.message))
                    return
        self._move_drivers()

    def _move_for_single_beamline_parameters(self, source):
        """
        Moves starts from a single beamline parameter and move is to parameters sp read backs. If the
        source is not in the mode then don't update any other parameters. Move to latest position.

        the beamline.
        Args:
            source: source to start the update from; None start from the beginning.
        """
        if self._active_mode.has_beamline_parameter(source):
            parameters = self._beamline_parameters.values()
            parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, source)

            for beamline_parameter in parameters_in_mode:
                beamline_parameter.move_to_sp_rbv_no_callback()
        self._move_drivers()

    def parameter(self, key):
        """
        Args:
            key (str): key of parameter to return

        Returns:
            ReflectometryServer.parameters.BeamlineParameter: the beamline parameter with the given key
        """
        return self._beamline_parameters[key]

    def _init_params_from_mode(self):
        """
        Applies the initial values set in the current beamline mode to the relevant beamline parameter setpoints.
        """
        for key, value in self._active_mode.initial_setpoints.items():
            self._beamline_parameters[key].sp_no_move = value

    def _get_drivers_not_at_setpoint(self):
        """
        Returns: A list of all drivers that are not already at their set point, i.e. need to be moved.
        """
        return [driver for driver in self._drivers if not driver.at_target_setpoint()]

    def _move_drivers(self):
        """
        Issue move for all drivers at the speed of the slowest axis and set appropriate status for failure/success.
        """
        try:
            self._perform_move_for_all_drivers(self._get_max_move_duration())
            self.set_status(STATUS.OKAY, "")
        except (ValueError, UnableToConnectToPVException) as e:
            self.set_status(STATUS.GENERAL_ERROR, e.message)

    def _perform_move_for_all_drivers(self, move_duration):
        for driver in self._drivers:
            driver.perform_move(move_duration)

    def _get_max_move_duration(self):
        max_move_duration = 0.0
        for driver in self._get_drivers_not_at_setpoint():
            max_move_duration = max(max_move_duration, driver.get_max_move_duration())

        return max_move_duration

    def set_status(self, status, message):
        """
        Set the status and message of the beamline.

        Args:
            status: status code
            message: message reflecting the status

        """
        self._status = status
        self._message = message
        self._trigger_status_change()

    def set_status_okay(self):
        """
        Convenience method to set a status of okay.
        """
        self.set_status(STATUS.OKAY, "")

    @property
    def status(self):
        """
        Returns:
            (STATUS): status code
        """
        return self._status

    @property
    def message(self):
        """
        Returns: the message which has been set
        """
        return self._message

    @property
    def status_codes(self):
        """
        Returns: the status codes which have display properties and alarm severities
        """
        # noinspection PyTypeChecker
        return [status.value for status in STATUS]

    def _initialise_mode(self, modes):
        """
        Tries to read and apply the last active mode from autosave file. Defaults to first mode in list if unsuccessful.

        Params:
            modes(list[BeamlineMode]): A list of all the modes in this configuration.
        """
        mode_name = read_mode()
        try:
            self._active_mode = self._modes[mode_name]
        except KeyError:
            logger.error("Mode {} not found in configuration. Setting default.".format(mode_name))
            if len(modes) > 0:
                self._active_mode = modes[0]

    def _trigger_active_mode_change(self):
        """
        Triggers all listeners after a mode change.

        """
        for listener in self._active_mode_change_listeners:
            listener(self.active_mode, self.get_param_names_in_mode())

    def add_active_mode_change_listener(self, listener):
        """
        Add a listener for mode changes to this beamline.

        Args:
            listener: the listener function to add with new mode as parameter
        """
        self._active_mode_change_listeners.add(listener)

    def _trigger_status_change(self):
        """
        Triggers all listeners after a status change.

        """
        for listener in self._status_change_listeners:
            listener(self.status, self.message)

    def add_status_change_listener(self, listener):
        """
        Add a listener for status changes to this beamline.

        Args:
            listener: the listener function to add with parameters for new status and message
        """
        self._status_change_listeners.add(listener)
