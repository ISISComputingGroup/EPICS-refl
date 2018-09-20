"""
Objects to Create a beamline from the configuration.
"""
import sys

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH
from ReflectometryServer.beamline import Beamline


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
        print(error.__class__.__name__ + ": " + error.message)
        beamline = Beamline([], [], [], [])
        beamline.error = "Can not read configuration, see ioc log for more information."

    return beamline
