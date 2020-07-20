"""
Objects to Create a beamline from the configuration.
"""
import logging
import os
import sys
import traceback
from importlib import import_module

from pcaspy import Severity

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH, REFL_IOC_NAME
from ReflectometryServer.beamline import Beamline, BeamlineMode, BeamlineConfigurationInvalidException
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo
from server_common.utilities import print_and_log, SEVERITY

DEFAULT_CONFIG_FILE = "config.py"


def _create_beamline_in_error(error_message):
    """
    Args:
        error_message: error message to set for beamline
    Returns: a blank beamline with an error status set

    """
    error_mode = BeamlineMode("No modes", [])
    beamline = Beamline([], [], [], [error_mode])
    try:
        STATUS_MANAGER.update_active_problems(
            ProblemInfo("Error reading configuration: {}".format(error_message), "Configuration", Severity.MAJOR_ALARM))
    except Exception as e:
        print(e)
    return beamline


def _get_config_to_load(macros):
    """
    Get the name of the config to load. Returns default if file name is invalid.

    Args:
        macros (dict): Dict of user-set IOC macros

    Returns: Name of the config to load
    """
    try:
        config_file = macros["CONFIG_FILE"]
        if len(config_file) > 0:
            config_file_to_load = config_file
        else:
            config_file_to_load = DEFAULT_CONFIG_FILE
    except KeyError:
        config_file_to_load = DEFAULT_CONFIG_FILE

    config_name = config_file_to_load[:-3]
    return config_name


def create_beamline_from_configuration(macros):
    """
    Create a beamline from a configuration file in the configuration area.

    Args:
        macros (dict): Dict of user-set IOC macros

    Returns: Configured beamline; on error returns blank beamline with error status.
    """

    try:
        print_and_log("Importing get_beamline function from config.py in {}".format(REFL_CONFIG_PATH),
                      SEVERITY.INFO, src=REFL_IOC_NAME)
        sys.path.insert(0, REFL_CONFIG_PATH)
        # noinspection PyUnresolvedReferences
        config_to_load = _get_config_to_load(macros)
        print_and_log("Importing get_beamline function from {} in {}".format(config_to_load, REFL_CONFIG_PATH),
                      SEVERITY.INFO, src=REFL_IOC_NAME)
        config = import_module(_get_config_to_load(macros))
        beamline = config.get_beamline(macros)

    except ImportError as error:

        print_and_log(error.__class__.__name__ + ": " + str(error), SEVERITY.MAJOR, src=REFL_IOC_NAME)

        beamline = _create_beamline_in_error("Configuration not found.")

    except BeamlineConfigurationInvalidException as error:
        print_and_log(error.__class__.__name__ + ": " + str(error), SEVERITY.MAJOR, src=REFL_IOC_NAME)
        traceback.print_exc(file=sys.stdout)
        beamline = _create_beamline_in_error("Beamline configuration is invalid.")

    except Exception as error:
        print_and_log(error.__class__.__name__ + ": " + str(error), SEVERITY.MAJOR, src=REFL_IOC_NAME)
        traceback.print_exc(file=sys.stdout)
        beamline = _create_beamline_in_error("Can not read configuration.")

    return beamline
