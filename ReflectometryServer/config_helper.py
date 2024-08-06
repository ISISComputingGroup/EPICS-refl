"""
Objects to help configure the beamline
"""

import logging
from typing import Any, Dict, List, Optional, Union

from pcaspy import Severity

from ReflectometryServer import (
    Beamline,
    BeamlineMode,
    ConstantCorrection,
    JawsCentrePVWrapper,
    JawsGapPVWrapper,
    ModeSelectCorrection,
    MotorPVWrapper,
    PVWrapper,
    SlitGapParameter,
)
from ReflectometryServer.parameters import (
    DEFAULT_RBV_TO_SP_TOLERANCE,
    BeamlineParameter,
    DirectParameter,
    EnumParameter,
)
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo

logger = logging.getLogger(__name__)

BLADE_DETAILS = {
    "N": {"name": "North", "pair": "S"},
    "S": {"name": "South", "pair": "N"},
    "E": {"name": "East", "pair": "W"},
    "W": {"name": "West", "pair": "E"},
}


class ConfigHelper:
    """
    Class holding configuration as it is built up
    """

    parameters = []
    constants = []
    components = []
    drivers = []
    modes = []
    mode_params = {}
    mode_is_disabled = {}
    mode_initial_values = {}
    beam_start = None
    footprint_setup = None

    @classmethod
    def reset(cls):
        cls.constants = []
        cls.parameters = []
        cls.components = []
        cls.drivers = []
        cls.modes = []
        cls.mode_params = {}
        cls.mode_is_disabled = {}
        cls.mode_initial_values = {}
        cls.beam_start = None
        cls.footprint_setup = None

    def __init__(self):
        logger.warning("This class is usually used statically")


def get_configured_beamline():
    """
    Returns: the configured beamline
    """
    modes = []
    for name in ConfigHelper.modes:
        modes.append(
            BeamlineMode(
                name,
                ConfigHelper.mode_params[name],
                ConfigHelper.mode_initial_values[name],
                ConfigHelper.mode_is_disabled[name],
            )
        )

    return Beamline(
        components=ConfigHelper.components,
        beamline_parameters=ConfigHelper.parameters,
        drivers=ConfigHelper.drivers,
        modes=modes,
        incoming_beam=ConfigHelper.beam_start,
        footprint_setup=ConfigHelper.footprint_setup,
        beamline_constants=ConfigHelper.constants,
    )


def add_constant(constant):
    """
    Add a beamline constant to the beamline configuration.

    Args:
        constant (ReflectometryServer.BeamlineConstant): beamline constant to add

    Returns:
        constant
    """
    ConfigHelper.constants.append(constant)
    return constant


def add_component(component, marker=None):
    """
    Add a beamline component to the beamline configuration.

    Args:
        component (ReflectometryServer.Component): beamline component
        marker: add component at the given marker; None add at the end

    Returns:
        component
    """
    if marker is None:
        ConfigHelper.components.append(component)
    else:
        ConfigHelper.components[marker] = component
    return component


def add_component_marker():
    """
    Add a marker in the components to be filled in later. Return that position.

    Returns: position that needs to be filled in
    """
    ConfigHelper.components.append(None)
    return len(ConfigHelper.components) - 1


def add_parameter(parameter, modes=None, mode_inits=None, marker=None):
    """
    Add a parameter to the beamline configuration.
    Args:
        parameter: parameter to add
        modes: a list of modes in which the parameter is in; None for not in a mode, e.g. (nr, polarised)
        mode_inits: a list of mode and their initial value; None for no init, e.g. [(nr, 0), (polarised, 1)]
        marker: index of location parameter should be added; None add to the end

    Returns:
        given parameter

    Example:
        Add name to nr and polarised mode
        >>> nr = add_mode("NR")
        >>> polarised = add_mode("POLARISED")
        >>> add_parameter(AxisParameter(ChangeAxis.POSITION, "name", component), modes=(nr, polarised))

        Add name to nr and polarised mode but with an initial value in nr of 0
        >>> nr = add_mode("NR")
        >>> polarised = add_mode("POLARISED")
        >>> add_parameter(
        ...     AxisParameter(ChangeAxis.POSITION, "name", component),
        ...     modes=(nr, polarised),
        ...     mode_inits=(nr, 0.0),
        ... )

    """
    if marker is None:
        ConfigHelper.parameters.append(parameter)
    else:
        ConfigHelper.parameters[marker] = parameter
    if modes is None:
        modes = []
    if isinstance(modes, str):
        modes = [modes]
    if mode_inits is None:
        mode_inits = []

    for mode in modes:
        ConfigHelper.mode_params[mode].append(parameter.name)

    for mode, init_value in mode_inits:
        ConfigHelper.mode_initial_values[mode][parameter.name] = init_value

    return parameter


def add_parameter_marker():
    """
    Add a marker in the parameters to be filled in later. Return that position.

    Returns: position that needs to be filled in
    """
    ConfigHelper.parameters.append(None)
    return len(ConfigHelper.parameters) - 1


def add_mode(name, is_disabled=False):
    """
    Add a mode to the config
    Args:
        name: name of the mode
        is_disabled: is a disabled mode

    Returns: mode

    """

    ConfigHelper.modes.append(name)
    ConfigHelper.mode_params[name] = []
    ConfigHelper.mode_initial_values[name] = {}
    ConfigHelper.mode_is_disabled[name] = is_disabled
    return name


def add_driver(driver, marker=None):
    """
    Add a driver to the config
    Args:
        driver: driver to add
        marker: add component at the given marker; None add to the end

    Returns: driver

    """
    if marker is None:
        ConfigHelper.drivers.append(driver)
    else:
        ConfigHelper.drivers[marker] = driver

    return driver


def add_driver_marker():
    """
    Add a marker in the drivers to be filled in later. Return that position.

    Returns: position that needs to be filled in
    """
    ConfigHelper.drivers.append(None)
    return len(ConfigHelper.drivers) - 1


def create_jaws_pv_driver(jaws_pv_prefix, is_vertical, is_gap_not_centre):
    """
    Create jaws pv driver. This is currently not a conventional driver and the beamline doesn't need it.
    Args:
        jaws_pv_prefix: prefix for the jaw, e.g. MOT:JAWS1
        is_vertical: True if vertical; False for horizontal
        is_gap_not_centre: True if for gap; False for centre

    Returns: driver

    """

    if is_gap_not_centre:
        return JawsGapPVWrapper(jaws_pv_prefix, is_vertical=is_vertical)
    else:
        return JawsCentrePVWrapper(jaws_pv_prefix, is_vertical=is_vertical)


def create_blade_pv_driver(jaws_pv_prefix: str, blade: str) -> PVWrapper:
    """
    Create a driver for a blade
    Args:
        jaws_pv_prefix: pv prefix
        blade: blade to set jaw for

    Returns: driver

    """
    return MotorPVWrapper("{}:J{}:MTR".format(jaws_pv_prefix, blade))


class SlitAxes:
    """
    Parameters relevant to slits. This is to avoid potential typos in the configuration file.
    """

    VertGap = "VG"
    VertCent = "VC"
    HorGap = "HG"
    HorCent = "HC"

    @staticmethod
    def all():
        """
        Gets all slit parameters: gaps and centres.
        :return: A list containing the gap and centre strings for templating PVs
        """
        return [SlitAxes.VertGap, SlitAxes.VertCent, SlitAxes.HorGap, SlitAxes.HorCent]

    @staticmethod
    def gaps():
        """
        Gets the gap PVs
        :return: A list containing the gap strings for templating PVs
        """
        return [SlitAxes.VertGap, SlitAxes.HorGap]

    @staticmethod
    def centres():
        """
        Gets the centre PVs
        :return: A list containing the centre strings for templating PVs
        """
        return [SlitAxes.VertCent, SlitAxes.HorCent]


def add_slit_parameters(
    slit_number: Union[str, int],
    rbv_to_sp_tolerance: float = DEFAULT_RBV_TO_SP_TOLERANCE,
    modes: Optional[List[str]] = None,
    mode_inits: Optional[Dict[str, Any]] = None,
    exclude: List[str] = None,
    include_centres: bool = False,
    beam_blocker: Optional[str] = None,
):
    """
    Add parameters for a slit, this is horizontal and vertical gaps and centres. Also add modes, mode inits and
    tolerance if needed.

    Args:
        slit_number: slit number to use. Assuming pv is of the form MOT:JAWS<slit number>
        rbv_to_sp_tolerance: tolerance to set in the parameter, shows an alarm if rbv is not within this tolerance
        modes: list of modes see add_parameter for explanation
        mode_inits: list of modes and init value see add_parameter for explanation
        exclude: slit parameters to exclude, these should be one of VG, VC, HG, HC
        include_centres: True to include centres; False to just have the gaps
        beam_blocker: string containing code for beam blocker config, N,S,E,W for each blade which blocks the beam

    Returns:
        slit gap parameters

    """

    if include_centres:
        names = SlitAxes.all()
    else:
        names = SlitAxes.gaps()
    if exclude is not None:
        names = [name for name in names if name not in exclude]

    jaws_pv_prefix = "MOT:JAWS{}".format(slit_number)

    parameters = _add_beam_block(
        slit_number, modes, mode_inits, exclude, beam_blocker, jaws_pv_prefix
    )

    for name in names:
        is_vertical = name[0] == "V"
        is_gap_not_centre = name[1] == "G"

        vg_param_name = "S{}{}".format(slit_number, name)
        driver = create_jaws_pv_driver(jaws_pv_prefix, is_vertical, is_gap_not_centre)
        parameter = SlitGapParameter(vg_param_name, driver, rbv_to_sp_tolerance=rbv_to_sp_tolerance)
        add_parameter(parameter, modes, mode_inits)
        parameters[name] = parameter

    return parameters


def _add_beam_block(
    slit_number, modes, mode_inits, exclude: List[str], beam_blocker: str, jaws_pv_prefix
) -> Dict[str, BeamlineParameter]:
    """
    Add beam block parameters and drivers
    Args:
        slit_number: slit number
        modes: modes that blocker parameter should belong to
        mode_inits: initialiser for each mode
        exclude: exclude these parameters
        beam_blocker: beam blocker slits
        jaws_pv_prefix: prefix for the jaw pv

    Returns:
        parameters in a dictionary
    """
    parameters = {}
    if beam_blocker is not None:
        options = ["No"]
        options.extend([BLADE_DETAILS[blade]["name"] for blade in beam_blocker])
        parameter = EnumParameter(
            "S{}BLOCK".format(slit_number),
            options,
            description="Which blade is blocking the beam; No for none",
        )
        add_parameter(parameter, modes, mode_inits)
        parameters["block"] = parameter
        blade_names = set()
        for blade in beam_blocker:
            blade_names.update(blade)
            blade_names.update(BLADE_DETAILS[blade]["pair"])
        if exclude is not None:
            [blade_names.discard(name) for name in exclude]
        # keep parameters ordered nicely
        for name in ["N", "S", "E", "W"]:
            if name in blade_names:
                driver = create_blade_pv_driver(jaws_pv_prefix, name)
                add_parameter(
                    DirectParameter("S{}{}".format(slit_number, name), driver), modes, mode_inits
                )
                parameters[name] = parameter
    return parameters


def add_beam_start(beam_start):
    """
    Add the beam start position and angle
    Args:
        beam_start: the beam start y, z and angle

    Returns:
        beam start

    Examples:
        >>> add_beam_start(PositionAndAngle(y, z, angle))
    """
    ConfigHelper.beam_start = beam_start
    return beam_start


def add_footprint_setup(footprint_setup):
    """
    Add footprint setup to the beamline
    Args:
        footprint_setup: footprint setup class

    Returns:
        footprint setup

    Examples:
        >>> add_footprint_setup(FootprintSetup(z_s1, z_s2, z_s3, z_s4, z_sample,
        >>>                                    s1_vgap_param, s2_vgap_param, s3_vgap_param, s4_vgap_param,
        >>>                                    theta_param_angle, lambda_min, lambda_max))

    """
    ConfigHelper.footprint_setup = footprint_setup
    return footprint_setup


def optional_is_set(optional_id, macros):
    """
    Check whether an optional macro for use in the configuration is set or not.

    Args:
        optional_id (String): The ID of the optional macro
        macros (dict): The macro values passed into the reflectometry server

    Returns: True if macro with given ID is set to True, otherwise False
    """
    try:
        macro_name = "OPTIONAL_{}".format(optional_id)
        macro_value = macros[macro_name]
        if macro_value.lower() == "true":
            return True
        elif macro_value.lower() == "false":
            return False
        else:
            STATUS_MANAGER.update_error_log(
                (
                    "Invalid value for IOC macro {}: {} (Expected: True/False)".format(
                        macro_name, macro_value
                    )
                )
            )
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Invalid IOC macro value", macro_name, Severity.MINOR_ALARM)
            )
            return False
    except KeyError:
        return False


def as_mode_correction(correction: float, modes: List[str], default: float = 0.0):
    """
    Helper method for creating a fixed offset engineering correction that gets applied for each mode in a given list.

    Args:
        correction: The value of the constant correction
        modes: The modes for which to apply the correction
        default: The value of the constant correction for all other modes

    Returns: True if macro with given ID is set to True, otherwise False
    """
    return ModeSelectCorrection(
        default_correction=ConstantCorrection(default),
        corrections_for_mode={mode: ConstantCorrection(correction) for mode in modes},
    )
