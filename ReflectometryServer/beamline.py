"""
Resources at a beamline level
"""
import logging
from collections import OrderedDict
from dataclasses import dataclass
from functools import partial

from pcaspy import Severity


from ReflectometryServer.beam_path_calc import BeamPathUpdate, BeamPathUpdateOnInit
from ReflectometryServer.exceptions import BeamlineConfigurationInvalidException, ParameterNotInitializedException
from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.file_io import mode_autosave, MODE_KEY
from ReflectometryServer.footprint_calc import BaseFootprintSetup
from ReflectometryServer.footprint_manager import FootprintManager
from ReflectometryServer.parameters import RequestMoveEvent
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo

from server_common.channel_access import UnableToConnectToPVException
from server_common.observable import observable

logger = logging.getLogger(__name__)


class BeamlineMode:
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

    def names_of_parameters_in_mode(self):
        return self._beamline_parameters_to_calculate

    #TODO move this to use above!
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

    def __repr__(self):
        return "{}({}, disabled={}, beamline_parameters{!r}, sp_inits{!r})".format(
            self.__class__.__name__, self.name, self.is_disabled, self._beamline_parameters_to_calculate,
            self._sp_inits)


@dataclass
class ActiveModeUpdate:
    """
    Event that is triggered when the active mode is changed
    """
    mode: BeamlineMode  # mode that has been changed to


@observable(ActiveModeUpdate)
class Beamline:
    """
    The collection of all beamline components.
    """

    def __init__(self, components, beamline_parameters, drivers, modes, incoming_beam=None,
                 footprint_setup=None, beamline_constants=None):
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
                Defaults to position 0,0 and angle 0 in mantid coordinates, i.e the natural beam as it enters the
                blockhouse.
            footprint_setup (ReflectometryServer.BaseFootprintSetup.BaseFootprintSetup): the foot print setup
            beamline_constants (list[ReflectometryServer.beamline_constant.BeamlineConstant]): beamline constants to
                expose
        """
        self._components = components
        self._beam_path_calcs_set_point = []
        self._beam_path_calcs_rbv = []
        self._beamline_parameters = OrderedDict()
        self._drivers = drivers
        footprint_setup = footprint_setup if footprint_setup is not None else BaseFootprintSetup()
        self.footprint_manager = FootprintManager(footprint_setup)
        for beamline_parameter in beamline_parameters:
            self._beamline_parameters[beamline_parameter.name] = beamline_parameter
            beamline_parameter.add_listener(RequestMoveEvent, self._move_for_single_beamline_parameters)

        self._modes = OrderedDict()
        for mode in modes:
            self._modes[mode.name] = mode

        self._validate(beamline_parameters, modes)

        for component in components:
            self._beam_path_calcs_set_point.append(component.beam_path_set_point)
            self._beam_path_calcs_rbv.append(component.beam_path_rbv)
            component.beam_path_set_point.add_listener(BeamPathUpdateOnInit, self.update_next_beam_component_on_init)
            component.beam_path_set_point.add_listener(BeamPathUpdate, partial(
                self.update_next_beam_component, calc_path_list=self._beam_path_calcs_set_point))
            component.beam_path_rbv.add_listener(BeamPathUpdate, partial(
                self.update_next_beam_component, calc_path_list=self._beam_path_calcs_rbv))
            component.beam_path_set_point.in_beam_manager.add_rbv_in_beam_manager(
                component.beam_path_rbv.in_beam_manager)

        self._incoming_beam = incoming_beam if incoming_beam is not None else PositionAndAngle(0, 0, 0)

        self.update_next_beam_component(BeamPathUpdate(None), self._beam_path_calcs_rbv)
        self.update_next_beam_component(BeamPathUpdate(None), self._beam_path_calcs_set_point)

        # Set observers on mode
        for driver in self._drivers:
            driver.set_observe_mode_change_on(self)

        # Initialised mode
        self._active_mode = None
        self._initialise_mode(modes)

        # Say whether to reinitialise the paramter mode_inits on a move all
        self.reinit_mode_on_move = False

        # initialise drivers (mode must be initialised first because of mode dependent engineering correction
        for driver in self._drivers:
            driver.set_observe_mode_change_on(self)
            driver.initialise()

        # set whether incoming beam can change dependent on current mode. Must do this after autosave and init because
        #  they will change the beam path
        self._set_incoming_beam_can_change()

        STATUS_MANAGER.set_initialised()

        if beamline_constants is not None:
            self.beamline_constants = beamline_constants
        else:
            self.beamline_constants = []

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
            STATUS_MANAGER.update_error_log(
                "Beamline configuration is invalid:\n    {}".format("\n    ".join(errors)))
            raise BeamlineConfigurationInvalidException("Beamline configuration invalid: {}".format(";".join(errors)))

    @property
    def parameters(self):
        """
        Returns:
            dict[str, ReflectometryServer.parameters.BeamlineParameter]: a dictionary of beamline parameters
        """
        return self._beamline_parameters

    @property
    def mode_names(self):
        """
        Returns: the names of all the modes
        """
        return list(self._modes.keys())

    @property
    def active_mode(self):
        """
        Returns: the name of the current modes; None for no active mode
        """
        try:
            return self._active_mode.name
        except AttributeError:
            STATUS_MANAGER.update_error_log("Error: No active beamline mode found.")
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
            logger.info("CHANGED ACTIVE MODE: {}".format(mode))
            for component in self._components:
                component.set_incoming_beam_can_change(not self._active_mode.is_disabled)
                mode_autosave.write_parameter(MODE_KEY, value=mode)
            self._init_params_from_mode()
            self.update_next_beam_component(BeamPathUpdate(None), self._beam_path_calcs_rbv)
            self.update_next_beam_component(BeamPathUpdate(None), self._beam_path_calcs_set_point)
            self.trigger_listeners(ActiveModeUpdate(self._active_mode))
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
        STATUS_MANAGER.clear_all()
        if self.reinit_mode_on_move:
            self._init_params_from_mode()
        self._move_for_all_beamline_parameters()

    def __getitem__(self, item):
        """
        Args:
            item: the index of the component

        Returns: the indexed component
        """
        return self._components[item]

    def get_param_names_in_mode(self):
        """ Returns a list of the name of params in the current mode, in order.
        """

        param_names_in_mode = []
        parameters = self._beamline_parameters.values()
        for param in self._active_mode.get_parameters_in_mode(parameters):
            param_names_in_mode.append(param.name)
        return param_names_in_mode

    def update_next_beam_component(self, update, calc_path_list):
        """
        Updates the next component in the beamline.

        Args:
            update(ReflectometryServer.beam_path_calc.BeamPathUpdateOnInit): Update event with source component of the
                update (or None for source if change is not originating from a component)
            calc_path_list(List[ReflectometryServer.components.BeamPathCalc]): list of beam calcs order in the same
                order as components
        """
        if update.source is None:
            outgoing = self._incoming_beam
            comp_index = -1
        else:
            outgoing = update.source.get_outgoing_beam()
            comp_index = calc_path_list.index(update.source)

        try:
            calc_path_list[comp_index + 1].set_incoming_beam(outgoing)
        except IndexError:
            pass  # no more components to update

    def update_next_beam_component_on_init(self, update):
        """
        Updates the next component in the beamline after an initialisation event, recalculating the setpoint beam path
        while preserving autosaved values.

        Args:
            update(ReflectometryServer.beam_path_calc.BeamPathUpdateOnInit): Update event with source component of the
                update (or None for source if change is not originating from a component)
        """
        if update.source is None:
            outgoing = self._incoming_beam
            comp_index = -1
        else:
            outgoing = update.source.get_outgoing_beam()
            comp_index = self._beam_path_calcs_set_point.index(update.source)

        try:
            next_component = self._beam_path_calcs_set_point[comp_index + 1]
            next_component.set_incoming_beam(outgoing, on_init=True)
        except IndexError:
            pass  # no more components to update

    def _move_for_all_beamline_parameters(self):
        """
        Updates the beamline parameters to the latest set point value; reapplies if they are in the mode. Then moves to
        latest positions.
        """
        logger.info("BEAMLINE MOVE TRIGGERED")
        parameters = self._beamline_parameters.values()
        parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, None)

        for beamline_parameter in parameters:
            if beamline_parameter in parameters_in_mode or beamline_parameter.sp_changed:
                try:
                    beamline_parameter.move_to_sp_no_callback()
                except ParameterNotInitializedException:
                    STATUS_MANAGER.update_active_problems(
                        ProblemInfo("Parameter not initialized. Is the configuration correct?", beamline_parameter.name,
                                    Severity.MAJOR_ALARM))
                    return

        self._move_drivers()

    def _move_for_single_beamline_parameters(self, request: RequestMoveEvent):
        """
        Moves starts from a single beamline parameter and move is to parameters sp read backs. If the
        request source is not in the mode then don't update any other parameters. Move to latest position.

        Args:
            request: request to move a single parameter; if source is None start from the beginning,
                otherwise start from source
        """
        STATUS_MANAGER.clear_all()
        logger.info("PARAMETER MOVE TRIGGERED (source: {})".format(request.source.name))
        if self._active_mode.has_beamline_parameter(request.source):
            parameters = self._beamline_parameters.values()
            parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, request.source)

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
            logger.info("Default value applied for param {}: {}".format(key, value))

    def _move_drivers(self):
        """
        Issue move for all drivers at the speed of the slowest axis and set appropriate status for failure/success.
        """
        try:
            self._perform_move_for_all_drivers(self._get_max_move_duration())
        except ZeroDivisionError as e:
            STATUS_MANAGER.update_error_log("Failed to perform beamline move: {}".format(e), e)
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Failed to move driver", "beamline", Severity.MAJOR_ALARM))
            return
        except (ValueError, UnableToConnectToPVException) as e:
            STATUS_MANAGER.update_error_log("Unable to connect to PV: {}".format(str(e)))
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Unable to connect to PV", "beamline", Severity.MAJOR_ALARM))
            return

    def _perform_move_for_all_drivers(self, move_duration):
        for driver in self._drivers:
            driver.perform_move(move_duration)

    def _get_max_move_duration(self):
        """
        Returns: maximum time taken for all required moves, if axes are not synchronised this will return 0 but
        movement will still be required

        """
        max_move_duration = 0.0
        for driver in self._drivers:
            max_move_duration = max(max_move_duration, driver.get_max_move_duration())

        logger.debug("Move duration for slowest axis: {:.2f}s".format(max_move_duration))
        return max_move_duration

    def _initialise_mode(self, modes):
        """
        Tries to read and apply the last active mode from autosave file. Defaults to first mode in list if unsuccessful.

        Args:
            modes(list[BeamlineMode]): A list of all the modes in this configuration.
        """
        mode_name = mode_autosave.read_parameter(MODE_KEY, default=None)
        initial_mode = None
        try:
            initial_mode = self._modes[mode_name]

        except KeyError:
            STATUS_MANAGER.update_error_log("Mode {} not found in configuration. Setting default.".format(mode_name))
            if len(modes) > 0:
                initial_mode = modes[0]
            else:
                STATUS_MANAGER.update_error_log("No modes have been configured.")

        if initial_mode is not None:
            self._active_mode = initial_mode
            self.trigger_listeners(ActiveModeUpdate(self._active_mode))

    def _set_incoming_beam_can_change(self):
        """
        During initialisation if the there is a mode set then set the incoming beam can change flag on
        all components
        """
        if self._active_mode is not None:
            mode_is_disabled = self._active_mode.is_disabled
            for component in self._components:
                component.set_incoming_beam_can_change(not mode_is_disabled, on_init=True)

    @property
    def drivers(self):
        """
        Returns: list of drivers in the beamline
        """
        return self._drivers
