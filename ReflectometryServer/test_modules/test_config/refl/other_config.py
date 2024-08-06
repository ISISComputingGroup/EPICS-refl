# FOR TESTING
# Valid configuration script for a reflectometry beamline

from ReflectometryServer import *

OTHER_CONFIG_PARAM = "other_config_param"


def get_beamline(macros):
    beam_angle_natural = -45
    perp_to_floor = 90.0

    # MODES
    nr = add_mode("nr")

    other_config_comp = add_component(
        Component("other_config_comp", PositionAndAngle(0.0, 1, perp_to_floor))
    )
    add_parameter(
        AxisParameter(OTHER_CONFIG_PARAM, other_config_comp, ChangeAxis.POSITION), modes=[nr]
    )

    add_beam_start(PositionAndAngle(0.0, 0.0, beam_angle_natural))

    return get_configured_beamline()
