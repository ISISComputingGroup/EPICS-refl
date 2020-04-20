"""
Objects to help configure the beamline
"""
from ReflectometryServer import Beamline, BeamlineMode, SlitGapParameter, JawsGapPVWrapper, JawsCentrePVWrapper
from ReflectometryServer.geometry import PositionAndAngle
import logging
import six

from ReflectometryServer.parameters import DEFAULT_RBV_TO_SP_TOLERANCE

logger = logging.getLogger(__name__)


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
        modes.append(BeamlineMode(name,
                                  ConfigHelper.mode_params[name],
                                  ConfigHelper.mode_initial_values[name],
                                  ConfigHelper.mode_is_disabled[name]))

    return Beamline(
        components=ConfigHelper.components,
        beamline_parameters=ConfigHelper.parameters,
        drivers=ConfigHelper.drivers,
        modes=modes,
        incoming_beam=ConfigHelper.beam_start,
        footprint_setup=ConfigHelper.footprint_setup,
        beamline_constants=ConfigHelper.constants)


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


def add_component(component):
    """
    Add a beamline component to the beamline configuration.

    Args:
        component (ReflectometryServer.Component): beamline component

    Returns:
        component
    """
    ConfigHelper.components.append(component)
    return component


def add_parameter(parameter, modes=None, mode_inits=None):
    """
    Add a parameter to the beamline configurarion
    Args:
        parameter: parameter to add
        modes: a list of modes in which the parameter is in; None for not in a mode, e.g. (nr, polarised)
        mode_inits: a list of mode and their initial value; None for no init, e.g. [(nr, 0), (polarised, 1)]

    Returns:
        given parameter

    Example:
        Add name to nr and polarised mode
        >>> nr = add_mode("NR")
        >>> polarised = add_mode("POLARISED")
        >>> add_parameter(TrackingPosition("name", component), modes=(nr, polarised))

        Add name to nr and polarised mode but with an initial value in nr of 0
        >>> nr = add_mode("NR")
        >>> polarised = add_mode("POLARISED")
        >>> add_parameter(TrackingPosition("name", component), modes=(nr, polarised), mode_inits=(nr, 0.0))

    """

    ConfigHelper.parameters.append(parameter)
    if modes is None:
        modes = []
    if isinstance(modes, six.string_types):
        modes = [modes]
    if mode_inits is None:
        mode_inits = []

    for mode in modes:
        ConfigHelper.mode_params[mode].append(parameter.name)

    for mode, init_value in mode_inits:
        ConfigHelper.mode_initial_values[mode][parameter.name] = init_value

    return parameter


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


def add_driver(driver):
    """
    Add a driver to the config
    Args:
        driver: driver to add

    Returns: driver

    """
    ConfigHelper.drivers.append(driver)

    return driver


def create_jaws_pv_driver(jaws_pv_prefix, is_vertical, is_gap_not_centre):
    """
    Create jaws pv driver. This is currently not a converntional driver and the beamline doesn't need it.
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


def add_slit_parameters(slit_number, rbv_to_sp_tolerance=DEFAULT_RBV_TO_SP_TOLERANCE, modes=None, mode_inits=None):
    """
    Add parameters for a slit, this is horizontal and vertical gaps and centres. Also add modes, mode inits and
    tolerance if needed.

    Args:
        slit_number: slit number to use. Assuming pv is of the form MOT:JAWS<slit number>
        rbv_to_sp_tolerance: tolerance to set in the parameter, shows an alarm if rbv is not within this tolerance
        modes: list of modes see add_parameter for explanation
        mode_inits: list of modes and init value see add_parameter for explanation

    Returns:
        slit gap parameters

    """

    jaws_pv_prefix = "MOT:JAWS{}".format(slit_number)

    parameters = []
    for name in ["VG", "VC", "HG", "HC"]:
        is_vertical = name[0] == "V"
        is_gap_not_centre = name[1] == "G"

        vg_param_name = "S{}{}".format(slit_number, name)
        driver = create_jaws_pv_driver(jaws_pv_prefix, is_vertical, is_gap_not_centre)
        parameter = SlitGapParameter(vg_param_name, driver, rbv_to_sp_tolerance=rbv_to_sp_tolerance)
        add_parameter(parameter, modes, mode_inits)
        parameters.append(parameter)

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
