"""
Reflectometry Server
"""

import logging.config
import os
import sys
from threading import Thread

from pcaspy import SimpleServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,  # this fixes the problem
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
            "pcaspy": {"handlers": ["default"], "level": "INFO", "propagate": True},
        },
    }
)

sys.path.insert(2, os.path.join(os.getenv("EPICS_KIT_ROOT"), "ISIS", "inst_servers", "master"))

try:
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ReflectometryServer.ChannelAccess.reflectometry_driver import ReflectometryDriver

from server_common.channel_access import ChannelAccess
from server_common.helpers import get_macro_values, register_ioc_start

from ReflectometryServer.beamline_configuration import create_beamline_from_configuration
from ReflectometryServer.ChannelAccess.constants import (
    DEFAULT_ASG_RULES,
    MYPVPREFIX,
    REFL_IOC_NAME,
    REFLECTOMETRY_PREFIX,
)
from ReflectometryServer.ChannelAccess.pv_manager import PVManager


def process_ca_loop():
    logger.info("Reflectometry Server processing requests")
    while True:
        try:
            SERVER.process(0.1)
            ChannelAccess.poll()
        except Exception:
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

# Run heartbeat IOC, this is done with a different prefix
SERVER.createPV(
    prefix="{pv_prefix}CS:IOC:{ioc_name}:DEVIOS:".format(
        pv_prefix=MYPVPREFIX, ioc_name=REFL_IOC_NAME
    ),
    pvdb={"HEARTBEAT": {"type": "int", "value": 0}},
)

driver = ReflectometryDriver(SERVER, pv_manager)

process_ca_thread = Thread(target=process_ca_loop)
process_ca_thread.daemon = True
process_ca_thread.start()

logger.info("Instantiating Beamline Model")
beamline = create_beamline_from_configuration(get_macro_values())
pv_manager.set_beamline(beamline)

# Do not re-create PVs that already exist
pvdb_to_add = pv_manager.get_init_filtered_pvdb()

SERVER.createPV(REFLECTOMETRY_PREFIX, pvdb_to_add)
driver.set_beamline(beamline)

register_ioc_start(REFL_IOC_NAME, pv_manager.PVDB, REFLECTOMETRY_PREFIX)

logger.info("Reflectometry IOC started.")

# Process CA transactions
process_ca_thread.join()
