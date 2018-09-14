"""
Reflectometry Server
"""

import sys
import os
from pcaspy import SimpleServer

try:
    from ReflServer.ChannelAccess.reflectometry_driver import ReflectometryDriver
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ReflServer.ChannelAccess.reflectometry_driver import ReflectometryDriver

from ReflServer.beamline_configuration import create_beamline_from_configuration
from ReflServer.ChannelAccess.constants import REFLECTOMETRY_PREFIX
from ReflServer.ChannelAccess.pv_manager import PVManager


beamline = create_beamline_from_configuration()

pv_db = PVManager(beamline.parameter_types, beamline.mode_names)
SERVER = SimpleServer()

print("Prefix: {}".format(REFLECTOMETRY_PREFIX))
SERVER.createPV(REFLECTOMETRY_PREFIX, pv_db.PVDB)

DRIVER = ReflectometryDriver(SERVER, beamline, pv_db)

# Process CA transactions
while True:
    try:
        SERVER.process(0.1)
    except Exception as err:
        print(err)
        break
