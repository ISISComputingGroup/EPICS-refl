"""
Reflectometry Server
"""

import logging.config
import sys
import os

from pcaspy import SimpleServer
from threading import Thread


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

sys.path.insert(2, os.path.join(os.getenv("EPICS_KIT_ROOT"), "ISIS", "inst_servers", "master"))

try:
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver

from ReflectometryServer.beamline_configuration import create_beamline_from_configuration
from ReflectometryServer.ChannelAccess.constants import REFLECTOMETRY_PREFIX, MYPVPREFIX, DEFAULT_ASG_RULES, \
    REFL_IOC_NAME
from ReflectometryServer.ChannelAccess.pv_manager import PVManager
from server_common.helpers import register_ioc_start
from server_common.channel_access import ChannelAccess


def process_ca_loop():
    logger.info("Reflectometry Server processing requests")
    while True:
        try:
            SERVER.process(0.1)
            ChannelAccess.poll()
        except Exception as err:
            break


logger.info("Initialising...")
logger.info("Prefix: {}".format(REFLECTOMETRY_PREFIX))

SERVER = SimpleServer()
# Add security access to pvs. NB this is only for local rules because we have not substituted in the correct macros for
# remote host access to the pvs
SERVER.initAccessSecurityFile(DEFAULT_ASG_RULES, P=MYPVPREFIX)

logger.info("Starting Reflectometry Driver")

# Create server status PVs only
pv_manager = PVManager()
SERVER.createPV(REFLECTOMETRY_PREFIX, pv_manager.PVDB)
driver = ReflectometryDriver(SERVER, pv_manager)

process_ca_thread = Thread(target=process_ca_loop)
process_ca_thread.daemon = True
process_ca_thread.start()

logger.info("Instantiating Beamline Model")
beamline = create_beamline_from_configuration()
pv_manager.set_beamline(beamline)

# Do not re-create PVs that already exist
pvdb_to_add = pv_manager.get_init_filtered_pvdb()

SERVER.createPV(REFLECTOMETRY_PREFIX, pvdb_to_add)
driver.set_beamline(beamline)

register_ioc_start(REFL_IOC_NAME, pv_manager.PVDB, REFLECTOMETRY_PREFIX)

logger.info("Reflectometry IOC started.")

# Process CA transactions
process_ca_thread.join()
