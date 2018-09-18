"""
Reflectometry Server
"""

import sys
import os
from pcaspy import SimpleServer

try:
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver

from ReflectometryServer.beamline_configuration import create_beamline_from_configuration
from ReflectometryServer.ChannelAccess.constants import REFLECTOMETRY_PREFIX
from ReflectometryServer.ChannelAccess.pv_manager import PVManager


beamline = create_beamline_from_configuration()

pv_db = PVManager(beamline.parameters.values(), beamline.mode_names)
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
