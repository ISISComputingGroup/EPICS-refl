"""
Resources at a beamline level
"""

from collections import OrderedDict, namedtuple
from functools import partial
from enum import Enum
from pcaspy import Severity

from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.footprint_calc import BlankFootprintCalculator

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

    def __init__(self, name, beamline_parameters_to_calculate, sp_inits=None):
        """
        Initialize.
        Args:
            name (str): name of the beam line mode
            beamline_parameters_to_calculate (list[str]): Beamline parameters in this mode
                which should be automatically moved to whenever a preceding parameter is changed
            sp_inits (dict[str, object]): The initial beamline parameter values that should be set when switching
                to this mode
        """
        self.name = name
        self._beamline_parameters_to_calculate = beamline_parameters_to_calculate
        if sp_inits is None:
            self._sp_inits = {}
        else:
            self._sp_inits = sp_inits

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

    def validate_parameters(self, beamline_parameters):
        """
        Validate the parameters in the mode against beamline parameters.
        Args:
            beamline_parameters: the beamline parameters
        Raises KeyError: If sp init or mode parameters name is not in list

        """
        for beamline_parameter in self._beamline_parameters_to_calculate:
            if beamline_parameter not in beamline_parameters:
                raise KeyError("Beamline parameter '{}' in mode '{}' not in beamline".format(
                    beamline_parameters, self.name))

        for sp_init in self._sp_inits.keys():
            if sp_init not in beamline_parameters:
                raise KeyError("SP Init '{}' in mode '{}' not in beamline".format(sp_init, self.name))


class Beamline(object):
    """
    The collection of all beamline components.
    """

    def __init__(self, components, beamline_parameters, drivers, modes, incoming_beam=PositionAndAngle(0, 0, 0),
                 footprint_calc=BlankFootprintCalculator()):
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
        """
        self._components = components
        self._beam_path_calcs_set_point = []
        self._beam_path_calcs_rbv = []
        self._footprint_calc = footprint_calc
        self._beamline_parameters = OrderedDict()
        self._drivers = drivers
        self._status = STATUS.OKAY
        self._message = ""

        for beamline_parameter in beamline_parameters:
            if beamline_parameter.name in self._beamline_parameters:
                raise ValueError("Beamline parameters must be uniquely named. Duplicate '{}'".format(
                    beamline_parameter.name))
            self._beamline_parameters[beamline_parameter.name] = beamline_parameter
            beamline_parameter.after_move_listener = self._move_for_single_beamline_parameters
            beamline_parameter.add_rbv_change_listener(self._footprint_calc.update_footprint)

        for component in components:
            self._beam_path_calcs_set_point.append(component.beam_path_set_point)
            self._beam_path_calcs_rbv.append(component.beam_path_rbv)
            component.beam_path_set_point.add_after_beam_path_update_listener(
                partial(self.update_next_beam_component, calc_path_list=self._beam_path_calcs_set_point))
            component.beam_path_rbv.add_after_beam_path_update_listener(
                partial(self.update_next_beam_component, calc_path_list=self._beam_path_calcs_rbv))

        self._modes = OrderedDict()
        for mode in modes:
            self._modes[mode.name] = mode
            mode.validate_parameters(self._beamline_parameters.keys())

        self._incoming_beam = incoming_beam
        self._active_mode = None
        self.update_next_beam_component(None, self._beam_path_calcs_set_point)
        self.update_next_beam_component(None, self._beam_path_calcs_rbv)

    @property
    def parameter_types(self):
        """
        Returns:
            dict[str, ReflectometryServer.parameters.BeamlineParameterType]: a dictionary of parameter type,
                keyed by their name
        """
        types = {}
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
            self.init_setpoints()
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
        self._move_drivers(self._get_max_move_duration())

    @property
    def beam_footprint(self):
        return self._footprint_calc.calc_footprint_penumbra()

    @property
    def beam_resolution(self):
        return self._footprint_calc.calc_min_resolution()

    @property
    def beam_q_range(self):
        return self._footprint_calc.calc_q_range()

    def __getitem__(self, item):
        """
        Args:
            item: the index of the component

        Returns: the indexed component
        """
        return self._components[item]

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

    def _move_for_all_beamline_parameters(self):
        """
        Updates the beamline parameters to the latest set point value; reapplies if they are in the mode.
        """
        parameters = self._beamline_parameters.values()
        parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, None)

        for beamline_parameter in parameters:
            if beamline_parameter in parameters_in_mode or beamline_parameter.sp_changed:
                beamline_parameter.move_to_sp_no_callback()

    def _move_for_single_beamline_parameters(self, source):
        """
        Moves starts from a single beamline parameter and move is to parameters sp read backs. If the
        source is not in the mode then don't update any other parameters.
        the beamline.
        Args:
            source: source to start the update from; None start from the beginning.
        """
        if self._active_mode.has_beamline_parameter(source):
            parameters = self._beamline_parameters.values()
            parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, source)

            for beamline_parameter in parameters_in_mode:
                beamline_parameter.move_to_sp_rbv_no_callback()

    def parameter(self, key):
        """
        Args:
            key (str): key of parameter to return

        Returns:
            ReflectometryServer.parameters.BeamlineParameter: the beamline parameter with the given key
        """
        return self._beamline_parameters[key]

    def init_setpoints(self):
        """
        Applies the initial values set in the current beamline mode to the relevant beamline parameter setpoints.
        """
        for key, value in self._active_mode.initial_setpoints.items():
            self._beamline_parameters[key].sp_no_move = value

    def _move_drivers(self, move_duration):
        for driver in self._drivers:
            driver.perform_move(move_duration)

    def _get_max_move_duration(self):
        max_move_duration = 0.0
        for driver in self._drivers:
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
        return [status.value for status in STATUS]
