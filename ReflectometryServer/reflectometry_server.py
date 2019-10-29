"""
Reflectometry Server
"""

import sys
import os

from pcaspy import SimpleServer
import logging.config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
             },
        'pcaspy': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True
            },
    }
})

try:
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver

from ReflectometryServer.beamline_configuration import create_beamline_from_configuration
from ReflectometryServer.ChannelAccess.constants import REFLECTOMETRY_PREFIX, MYPVPREFIX, DEFAULT_ASG_RULES
from ReflectometryServer.ChannelAccess.pv_manager import PVManager
from server_common.ioc_data_source import IocDataSource
from server_common.channel_access import ChannelAccess
from server_common.mysql_abstraction_layer import SQLAbstraction

logger.info("Initialising...")
beamline = create_beamline_from_configuration()

pv_db = PVManager(beamline)
SERVER = SimpleServer()
SERVER.initAccessSecurityFile(DEFAULT_ASG_RULES, P=MYPVPREFIX)

print("Prefix: {}".format(REFLECTOMETRY_PREFIX))
SERVER.createPV(REFLECTOMETRY_PREFIX, pv_db.PVDB)

DRIVER = ReflectometryDriver(SERVER, beamline, pv_db)

ioc_data_source = IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb"))
ioc_data_source.insert_ioc_start("REFL", os.getpid(), sys.argv[0], pv_db.PVDB, REFLECTOMETRY_PREFIX)

logger.info("Reflectometry IOC started")

# Process CA transactions

while True:
    try:
        SERVER.process(0.1)
        ChannelAccess.poll()
    except Exception as err:
        print(err)
        break
