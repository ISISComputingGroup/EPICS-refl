"""
Objects to Create a beamline from the configuration.
"""
import sys

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline, STATUS
from server_common.utilities import print_and_log, SEVERITY


def create_default_beamline():
    beamline = Beamline([], [], [], [])
    beamline.incoming_beam = (0, 0, 0)
    return beamline

def create_beamline_from_configuration():
    """
    Returns: Beamline
    """

    try:
        sys.path.insert(0, REFL_CONFIG_PATH + '\\refl')
        from config import get_beamline

        beamline = get_beamline()
        beamline.active_mode = "nr"  # TODO initialise in init (future ticket)
        beamline.status = STATUS.OKAY
    except ImportError as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = create_default_beamline()
        beamline.status = STATUS.CONFIG_IMPORT_ERROR
        beamline.message = "Can not import configuration, check config script name. See ioc log for more information."
    except Exception as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = create_default_beamline()
        beamline.status = STATUS.CONFIG_ERROR
        beamline.message = "Can not read configuration, see ioc log for more information."

    return beamline
