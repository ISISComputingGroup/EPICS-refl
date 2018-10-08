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
from server_common.ioc_data_source import IocDataSource
from server_common.mysql_abstraction_layer import SQLAbstraction


beamline = create_beamline_from_configuration()

pv_db = PVManager(beamline.parameter_types, beamline.mode_names)
SERVER = SimpleServer()

print("Prefix: {}".format(REFLECTOMETRY_PREFIX))
SERVER.createPV(REFLECTOMETRY_PREFIX, pv_db.PVDB)

DRIVER = ReflectometryDriver(SERVER, beamline, pv_db)

ioc_data_source = IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb"))
ioc_data_source.insert_ioc_start("REFL", os.getpid(), sys.argv[0], pv_db.PVDB, REFLECTOMETRY_PREFIX)

# Process CA transactions
while True:
    try:
        SERVER.process(0.1)
    except Exception as err:
        print(err)
        break
