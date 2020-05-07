"""
Objects to Create a beamline from the configuration.
"""
from builtins import str
import sys
import traceback

from pcaspy import Severity

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline, BeamlineMode, BeamlineConfigurationInvalidException
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo
from server_common.utilities import print_and_log, SEVERITY


def _create_beamline_in_error(error_message):
    """
    Args:
        error_message: error message to set for beamline
    Returns: a blank beamline with an error status set

    """
    error_mode = BeamlineMode("No modes", [])
    beamline = Beamline([], [], [], [error_mode])
    STATUS_MANAGER.update_active_problems(
        ProblemInfo("Error reading configuration: {}".format(error_message), "Configuration", Severity.MAJOR_ALARM))
    return beamline


def create_beamline_from_configuration():
    """
    Create a beamline from a configuration file in the configuration area.

    Returns: Configured beamline; on error returns blank beamline with error status.
    """

    try:
        print_and_log("Importing get_beamline function from config.py in {}".format(REFL_CONFIG_PATH),
                      SEVERITY.INFO, src="REFL")
        sys.path.insert(0, REFL_CONFIG_PATH)
        # noinspection PyUnresolvedReferences
        from config import get_beamline

        beamline = get_beamline()

    except ImportError as error:

        print_and_log(error.__class__.__name__ + ": " + str(error), SEVERITY.MAJOR, src="REFL")

        beamline = _create_beamline_in_error("Configuration not found.")

    except BeamlineConfigurationInvalidException as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        traceback.print_exc(file=sys.stdout)
        beamline = _create_beamline_in_error("Beamline configuration is invalid.")

    except Exception as error:
        print_and_log(error.__class__.__name__ + ": " + str(error), SEVERITY.MAJOR, src="REFL")
        traceback.print_exc(file=sys.stdout)
        beamline = _create_beamline_in_error("Can not read configuration.")

    return beamline
