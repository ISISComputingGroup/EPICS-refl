"""
Objects to Create a beamline from the configuration.
"""
import os
import sys

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline, STATUS
from server_common.utilities import print_and_log, SEVERITY


def _create_beamline_in_error(error_message):
    """
    Args:
        error_message: error message to set for beamline
    Returns: a blank beamline with an error status set

    """
    beamline = Beamline([], [], [], [])
    beamline.incoming_beam = (0, 0, 0)
    beamline.set_status(STATUS.CONFIG_ERROR, error_message)
    return beamline


def create_beamline_from_configuration():
    """
    Create a beamline from a configuration file in the configuration area.

    Returns: Configured beamline; on error returns blank beamline with error status.
    """

    try:
        sys.path.insert(0, os.path.join(REFL_CONFIG_PATH, 'refl'))
        from config import get_beamline

        beamline = get_beamline()
        beamline.active_mode = "nr"  # TODO initialise in init (future ticket)
        beamline.set_status_okay()
    except ImportError as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = _create_beamline_in_error("Can not import configuration, check config script name. "
                                             "See ioc log for more information.")

    except Exception as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = _create_beamline_in_error("Can not read configuration, see ioc log for more information.")

    return beamline
