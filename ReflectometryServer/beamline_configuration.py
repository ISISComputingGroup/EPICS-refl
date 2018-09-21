"""
Objects to Create a beamline from the configuration.
"""
import sys

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline, STATUS
from server_common.utilities import print_and_log, SEVERITY


def create_beamline_from_configuration():
    """
    Returns: Beamline, should be from configuration but is just from a hard coded beamline
    """

    try:
        sys.path.insert(0, REFL_CONFIG_PATH + '/refl')

        from configuration import get_beamline

        beamline = get_beamline()
        beamline.active_mode = "nr"  #TODO initialise in init (future ticket)
    except ImportError as error:
        print_and_log(error.__class__.__name__ + ": " + error.message, SEVERITY.MAJOR, src="REFL")
        beamline = Beamline([], [], [], [])
        beamline.status = STATUS.CONFIG_ERROR
        beamline.message = "Can not read configuration, see ioc log for more information."

    return beamline
