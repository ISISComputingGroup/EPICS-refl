# FOR TESTING
# Valid configuration script for a reflectometry beamline

from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import create_mock_axis


def get_beamline():
    beam_angle_natural = -45
    perp_to_floor = 90.0

    # MODES
    nr = add_mode("nr")
    pnr = add_mode("pnr")
    disabled = add_mode("disabled", is_disabled=True)

    add_component(Component("s1", PositionAndAngle(0.0, 1, perp_to_floor)))

    super_mirror = add_component(ReflectingComponent("sm", PositionAndAngle(0.0, 5, perp_to_floor)))
    add_parameter(InBeamParameter("smenabled", super_mirror), modes=[pnr], mode_inits={nr: False, pnr: True})
    add_parameter(AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE), modes=[pnr], mode_inits={nr: 0.0, pnr: 0.5})
    add_driver(IocDriver(super_mirror, ChangeAxis.POSITION, create_mock_axis("MOT:MTR0101", 0, 1),
                         out_of_beam_positions=[OutOfBeamPosition(position=-10)]))

    s2 = add_component(Component("s2", PositionAndAngle(0.0, 9, perp_to_floor)))
    add_parameter(AxisParameter("slit2pos", s2, ChangeAxis.POSITION), modes=[nr, pnr])

    sample = add_component(ReflectingComponent("sample", PositionAndAngle(0.0, 10, perp_to_floor)))
    add_parameter(AxisParameter("samplepos", sample, ChangeAxis.POSITION), modes=[nr, pnr])

    theta_comp = add_component_marker()
    theta_parameter =add_parameter_marker()


    s3 = add_component(Component("s3", PositionAndAngle(0.0, 15, perp_to_floor)))
    add_parameter(AxisParameter("slit3pos", s3, ChangeAxis.POSITION), modes=[nr, pnr])

    s4 = add_component(Component("s4", PositionAndAngle(0.0, 19, perp_to_floor)))
    add_parameter(AxisParameter("slit4pos", s4, ChangeAxis.POSITION), modes=[nr, pnr])

    point_det = add_component(TiltingComponent("det", PositionAndAngle(0.0, 20, perp_to_floor)))
    add_parameter(AxisParameter("detpos", point_det, ChangeAxis.POSITION), modes=[nr, pnr, disabled])

    theta = add_component(ThetaComponent("THETA", PositionAndAngle(0, 10, perp_to_floor), angle_to=[point_det]),
                          marker=theta_comp)
    add_parameter(AxisParameter("theta", theta, ChangeAxis.ANGLE), modes=[nr, pnr], marker=theta_parameter)

    add_beam_start(PositionAndAngle(0.0, 0.0, beam_angle_natural))

    return get_configured_beamline()
