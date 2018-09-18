"""
Resources at a beamline level
"""
from collections import OrderedDict


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
            sp_inits (dict[str, object]): The initial beamline parameter values that should be set when switching to this mode
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
            beamline_parameter(ReflServer.parameters.BeamlineParameter): the beamline parameter

        Returns: True if beamline_parameter is in this mode.
        """
        return beamline_parameter.name in self._beamline_parameters_to_calculate

    def get_parameters_in_mode(self, beamline_parameters, first_parameter=None):
        """
        Returns, in order, all those parameters which are in this mode. Starting with the parameter after the first
        parameter
        Args:
            beamline_parameters(list[ReflServer.parameters.BeamlineParameter]): the beamline parameters which
                maybe in the mode
            first_parameter(ReflServer.parameters.BeamlineParameter): the parameter after which to include parameters;
                None for include all

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

    def __init__(self, components, beamline_parameters, drivers, modes):
        """
        The initializer.
        Args:
            components (list[ReflServer.components.Component]): The collection of beamline components
            beamline_parameters (list[ReflServer.parameters.BeamlineParameter]): a dictionary of parameters that
                characterise the beamline
            drivers(list[ReflServer.ioc_driver.IocDriver]): a list of motor drivers linked to a component in the
                beamline
            modes(list[BeamlineMode])
        """
        self._components = components
        self._beamline_parameters = OrderedDict()
        self._drivers = drivers

        for beamline_parameter in beamline_parameters:
            if beamline_parameter.name in self._beamline_parameters:
                raise ValueError("Beamline parameters must be uniquely named. Duplicate '{}'".format(
                    beamline_parameter.name))
            self._beamline_parameters[beamline_parameter.name] = beamline_parameter
            beamline_parameter.after_move_listener = self.update_beamline_parameters

        for component in components:
            component.after_beam_path_update_listener = self.update_beam_path

        self._modes = OrderedDict()
        for mode in modes:
            self._modes[mode.name] = mode
            mode.validate_parameters(self._beamline_parameters.keys())

        self.incoming_beam = None
        self._active_mode = None

    @property
    def parameter_types(self):
        """
        Returns:
            dict[str, ReflServer.parameters.BeamlineParameterType]:a dictionary of parmeter type, keyed by their name
        """
        types = {}
        for beamline_parameter in self._beamline_parameters.values():
            types[beamline_parameter.name] = beamline_parameter.parameter_type
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
        Returns: the name of the current modes
        """
        print(self._active_mode)
        return self._active_mode.name

    @active_mode.setter
    def active_mode(self, mode):
        """
        Set the current mode (setting presets as expected)
        Args:
            mode (str): name of the mode to set
        """
        try:
            print(mode)
            self._active_mode = self._modes[mode]
            print(self._active_mode)
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
        self.update_beamline_parameters()
        self._move_drivers(self._get_max_move_duration())

    def __getitem__(self, item):
        """
        Args:
            item: the index of the component

        Returns: the indexed component
        """
        return self._components[item]

    def set_incoming_beam(self, incoming_beam):
        """
        Set the incoming beam for the component
        Args:
            incoming_beam: incoming beam
        """
        self.incoming_beam = incoming_beam
        self.update_beam_path(None)

    def update_beam_path(self, source_component):
        """
        Updates the beam path for all components
        Args:
            source_component: source component of the update or None for not from component change
        """
        outgoing = self.incoming_beam
        for component in self._components:
            component.set_incoming_beam(outgoing)
            outgoing = component.get_outgoing_beam()

    def update_beamline_parameters(self, source=None):
        """
        Updates the beamline parameters in the current mode. If given a source in the mode start from this one instead
        of from the beginning of the beamline. If the source is not in the mode then don't update the beamline.
        Args:
            source: source to start the update from; None start from the beginning.

        Returns:

        """
        if source is None or self._active_mode.has_beamline_parameter(source):
            parameters = self._beamline_parameters.values()
            parameters_in_mode = self._active_mode.get_parameters_in_mode(parameters, source)

            for beamline_parameter in parameters:
                if beamline_parameter in parameters_in_mode or beamline_parameter.sp_changed:
                    beamline_parameter.move_no_callback()

    def parameter(self, key):
        """
        Args:
            key (str): key of parameter to return

        Returns:
            ReflServer.parameters.BeamlineParameter: the beamline parameter with the given key
        """
        return self._beamline_parameters[key]

    def get_mode_by_index(self, index):
        """
        Get the mode by the mode name
        Args:
            index(str): name of mode to return

        Returns:
            BeamlineMode: the beamline mode associated with the key

        """
        key = self._modes.keys()[index]
        return self.mode(key)

    def mode(self, key):
        """
        Args:
            key: key of parameter to return

        Returns (ReflectometryServer.parameters.BeamlineParameter):
            the beamline parameter with the given key
        """
        return self._modes[key]

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
