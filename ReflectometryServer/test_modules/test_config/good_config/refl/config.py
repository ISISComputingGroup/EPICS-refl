# FOR TESTING
# Valid configuration script for a refelctometry beamline

from ReflectometryServer.components import *
from ReflectometryServer.geometry import *
from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.parameters import *
from ReflectometryServer.movement_strategy import LinearSetup

def get_beamline():
    beam_angle_natural = -45
    perp_to_floor = 90.0
    # COMPONENTS
    # s1 = Component("s1", LinearSetup(0.0, 7.3025, perp_to_beam_angle))
    # s2 = Component("s2", LinearSetup(0.0, 9.6885, perp_to_beam_angle))
    # s3 = Component("s3", LinearSetup(0.0, 10.651, perp_to_beam_angle))
    # s4 = Component("s4", LinearSetup(0.0, 11.983, perp_to_beam_angle))
    # super_mirror = ReflectingComponent("sm", LinearSetup(0.0, 7.7685, perp_to_beam_angle))
    # sample = ReflectingComponent("sample", LinearSetup(0.0, 10.25, perp_to_beam_angle))
    # point_det = TiltingJaws("pdet", LinearSetup(0.0, 12.113, perp_to_beam_angle))
    s1 = Component("s1", LinearSetup(0.0, 1, perp_to_floor))
    super_mirror = ReflectingComponent("sm", LinearSetup(0.0, 5, perp_to_floor))
    s2 = Component("s2", LinearSetup(0.0, 9, perp_to_floor))
    sample = ReflectingComponent("sample", LinearSetup(0.0, 10, perp_to_floor))
    s3 = Component("s3", LinearSetup(0.0, 15, perp_to_floor))
    s4 = Component("s4", LinearSetup(0.0, 19, perp_to_floor))
    point_det = TiltingJaws("det", LinearSetup(0.0, 20, perp_to_floor))
    comps = [s1, super_mirror, s2, sample, s3, s4, point_det]

    # BEAMLINE PARAMETERS
    sm_enabled = ComponentEnabled("smenabled", super_mirror, True)
    sm_angle = AngleParameter("smangle", super_mirror, True)
    slit2_pos = TrackingPosition("slit2pos", s2, True)
    sample_pos = TrackingPosition("samplepos", sample, True)
    theta = AngleParameter("theta", sample, True)
    slit3_pos = TrackingPosition("slit3pos", s3, True)
    slit4_pos = TrackingPosition("slit4pos", s4, True)
    det = TrackingPosition("detpos", point_det, True)
    params = [sm_enabled,
              sm_angle,
              slit2_pos,
              sample_pos,
              theta,
              slit3_pos,
              slit4_pos,
              det]

    # MODES
    nr_inits = {"smenabled": False, "smangle": 0.0}
    pnr_inits = {"smenabled": True, "smangle": 0.5}
    nr_mode = BeamlineMode("nr", [param.name for param in params if param.name is not "smangle"], nr_inits)
    pnr_mode = BeamlineMode("pnr", [param.name for param in params], pnr_inits)
    disabled_mode = BeamlineMode("disabled", [])
    modes = [nr_mode, pnr_mode, disabled_mode]

    beam_start = PositionAndAngle(0.0, 0.0, beam_angle_natural)
    bl = Beamline(comps, params, [], modes, beam_start)

    return bl
