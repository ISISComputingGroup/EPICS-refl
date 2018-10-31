"""
Objects to Create a beamline from the configuration.
"""
import os
import sys

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline, STATUS, BeamlineMode
from server_common.utilities import print_and_log, SEVERITY


def _create_beamline_in_error(error_message):
    """
    Args:
        error_message: error message to set for beamline
    Returns: a blank beamline with an error status set

    """
    error_mode = BeamlineMode("No modes", [])
    beamline = Beamline([], [], [], [error_mode])
    beamline.incoming_beam = (0, 0, 0)
    beamline.set_status(STATUS.CONFIG_ERROR, error_message)
    return beamline


def create_beamline_from_configuration():
    """
    Create a beamline from a configuration file in the configuration area.

    Returns: Configured beamline; on error returns blank beamline with error status.
    """

    try:
        import_path = os.path.abspath(os.path.join(REFL_CONFIG_PATH, 'refl'))
        print_and_log("Importing get_beamline function from config.py in {}".format(import_path),
                      SEVERITY.INFO, src="REFL")
        sys.path.insert(0, import_path)
        from config import get_beamline

        beamline = get_beamline()
        beamline.set_status_okay()
    except ImportError as error:

        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")

        beamline = _create_beamline_in_error("Configuration not found.")

    except Exception as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = _create_beamline_in_error("Can not read configuration.")

    beamline.active_mode = beamline.mode_names[0]  # TODO initialise in init (future ticket)
    return beamline
