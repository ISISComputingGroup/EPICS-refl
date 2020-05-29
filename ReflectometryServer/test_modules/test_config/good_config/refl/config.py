# FOR TESTING
# Valid configuration script for a refelctometry beamline

from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import create_mock_axis


def get_beamline():
    beam_angle_natural = -45
    perp_to_floor = 90.0
    # COMPONENTS
    # s1 = Component("s1", PositionAndAngle(0.0, 7.3025, perp_to_beam_angle))
    # s2 = Component("s2", PositionAndAngle(0.0, 9.6885, perp_to_beam_angle))
    # s3 = Component("s3", PositionAndAngle(0.0, 10.651, perp_to_beam_angle))
    # s4 = Component("s4", PositionAndAngle(0.0, 11.983, perp_to_beam_angle))
    # super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 7.7685, perp_to_beam_angle))
    # sample = ReflectingComponent("sample", PositionAndAngle(0.0, 10.25, perp_to_beam_angle))
    # point_det = TiltingComponent("pdet", PositionAndAngle(0.0, 12.113, perp_to_beam_angle))
    s1 = Component("s1", PositionAndAngle(0.0, 1, perp_to_floor))
    super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 5, perp_to_floor))
    s2 = Component("s2", PositionAndAngle(0.0, 9, perp_to_floor))
    sample = ReflectingComponent("sample", PositionAndAngle(0.0, 10, perp_to_floor))
    s3 = Component("s3", PositionAndAngle(0.0, 15, perp_to_floor))
    s4 = Component("s4", PositionAndAngle(0.0, 19, perp_to_floor))
    point_det = TiltingComponent("det", PositionAndAngle(0.0, 20, perp_to_floor))
    comps = [s1, super_mirror, s2, sample, s3, s4, point_det]

    # BEAMLINE PARAMETERS
    sm_enabled = InBeamParameter("smenabled", super_mirror)
    sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
    slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)
    sample_pos = AxisParameter("samplepos", sample, ChangeAxis.POSITION)
    theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)
    slit3_pos = AxisParameter("slit3pos", s3, ChangeAxis.POSITION)
    slit4_pos = AxisParameter("slit4pos", s4, ChangeAxis.POSITION)
    det = AxisParameter("detpos", point_det, ChangeAxis.POSITION)
    params = [sm_enabled,
              sm_angle,
              slit2_pos,
              sample_pos,
              theta,
              slit3_pos,
              slit4_pos,
              det]

    # Drivers

    drivers = [DisplacementDriver(super_mirror, create_mock_axis("MOT:MTR0101", 0, 1), out_of_beam_position=-10)]

    # MODES
    nr_inits = {"smenabled": False, "smangle": 0.0}
    pnr_inits = {"smenabled": True, "smangle": 0.5}
    nr_mode = BeamlineMode("nr", [param.name for param in params if param.name is not "smangle"], nr_inits)
    pnr_mode = BeamlineMode("pnr", [param.name for param in params], pnr_inits)
    disabled_mode = BeamlineMode("disabled", [])
    modes = [nr_mode, pnr_mode, disabled_mode]

    beam_start = PositionAndAngle(0.0, 0.0, beam_angle_natural)
    bl = Beamline(comps, params, drivers, modes, beam_start)

    return bl
