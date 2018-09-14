from pcaspy import SimpleServer
from src.ChannelAccess.macros import *
from src.components import *
from src.beamline import Beamline, BeamlineMode
from src.parameters import *
from src.ChannelAccess.pv_server import ReflectometryDriver
from src.ChannelAccess.pv_manager import PVManager
from src.movement_strategy import LinearMovement

STATUS_PV_FIELDS = {'type': 'enum', 'enums': ["OUT", "IN"]}
FLOAT_PV_FIELDS = {'type': 'float', 'prec': 3, 'value': 0.0}
PARAMS_FIELDS = {"smenabled": STATUS_PV_FIELDS,
                 "smangle": FLOAT_PV_FIELDS,
                 "slit2pos": FLOAT_PV_FIELDS,
                 "samplepos": FLOAT_PV_FIELDS,
                 "theta": FLOAT_PV_FIELDS,
                 "slit3pos": FLOAT_PV_FIELDS,
                 "slit4pos": FLOAT_PV_FIELDS,
                 "detpos": FLOAT_PV_FIELDS,
                 }


def create_beamline():
    beam_angle_natural = -45
    beam_start = PositionAndAngle(0.0, 0.0, beam_angle_natural)
    perp_to_floor = 90.0

    # COMPONENTS
    # s1 = Component("s1", LinearMovement(0.0, 7.3025, perp_to_beam_angle))
    # s2 = Component("s2", LinearMovement(0.0, 9.6885, perp_to_beam_angle))
    # s3 = Component("s3", LinearMovement(0.0, 10.651, perp_to_beam_angle))
    # s4 = Component("s4", LinearMovement(0.0, 11.983, perp_to_beam_angle))
    # super_mirror = ReflectingComponent("sm", LinearMovement(0.0, 7.7685, perp_to_beam_angle))
    # sample = ReflectingComponent("sample", LinearMovement(0.0, 10.25, perp_to_beam_angle))
    # point_det = TiltingJaws("pdet", LinearMovement(0.0, 12.113, perp_to_beam_angle))
    s1 = Component("s1", LinearMovement(0.0, 1, perp_to_floor))
    super_mirror = ReflectingComponent("sm", LinearMovement(0.0, 5, perp_to_floor))
    s2 = Component("s2", LinearMovement(0.0, 9, perp_to_floor))
    sample = ReflectingComponent("sample", LinearMovement(0.0, 10, perp_to_floor))
    s3 = Component("s3", LinearMovement(0.0, 15, perp_to_floor))
    s4 = Component("s4", LinearMovement(0.0, 19, perp_to_floor))
    point_det = TiltingJaws("det", LinearMovement(0.0, 20, perp_to_floor))
    comps = [s1, super_mirror, s2, sample, s3, s4, point_det]

    # BEAMLINE PARAMETERS
    sm_enabled = ComponentEnabled("smenabled", super_mirror, True)
    sm_angle = ReflectionAngle("smangle", super_mirror, True)
    slit2_pos = TrackingPosition("slit2pos", s2, True)
    sample_pos = TrackingPosition("samplepos", sample, True)
    theta = Theta("theta", sample, True)
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

    nr_inits = {"smenabled": False, "smangle": 0.0}
    pnr_inits = {"smenabled": True, "smangle": 0.5}

    nr_mode = BeamlineMode("nr", [param for param in PARAMS_FIELDS.keys() if param is not "smangle"], nr_inits)
    pnr_mode = BeamlineMode("pnr", PARAMS_FIELDS.keys(), pnr_inits)
    disabled_mode = BeamlineMode("disabled", [])

    modes = [nr_mode, pnr_mode, disabled_mode]

    # init beamline
    bl = Beamline(comps, params, [], modes)
    bl.set_incoming_beam(beam_start)
    bl.active_mode = nr_mode
    return bl, modes


beamline, modes = create_beamline()

pv_db = PVManager(PARAMS_FIELDS, [mode.name for mode in modes])
SERVER = SimpleServer()
print("Prefix: {}".format(REFLECTOMETRY_PREFIX))
for pv_name in pv_db.PVDB.keys():
    print("creating pv: {}".format(pv_name))
SERVER.createPV(REFLECTOMETRY_PREFIX, pv_db.PVDB)
DRIVER = ReflectometryDriver(SERVER, beamline, pv_db)

# Process CA transactions
while True:
    try:
        SERVER.process(0.1)
    except Exception as err:
        print(err)
        break
