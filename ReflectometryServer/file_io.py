"""
file io for various autosave and other parts of the system
"""

import logging

from enum import Enum

from ReflectometryServer.ChannelAccess.constants import REFL_AUTOSAVE_PATH
from server_common.autosave import AutosaveFile
from server_common.utilities import print_and_log, SEVERITY

logger = logging.getLogger(__name__)

PARAM_AUTOSAVE_FILE = "params"
VELOCITY_AUTOSAVE_FILE = "velocity"
MODE_AUTOSAVE_FILE = "mode"

MODE_KEY = "mode"


class AutosaveType(Enum):
    """
    Different types of autosave.
    """
    # parameter autosave
    PARAM = 0

    # Velocity autosave
    VELOCITY = 1

    # Modes autosave
    MODE = 2

    @staticmethod
    def filename(autosave_type):
        if autosave_type == AutosaveType.PARAM:
            return PARAM_AUTOSAVE_FILE
        elif autosave_type == AutosaveType.VELOCITY:
            return VELOCITY_AUTOSAVE_FILE
        elif autosave_type == AutosaveType.MODE:
            return MODE_AUTOSAVE_FILE
        else:
            print_and_log("Error: file path requested for unknown autosave type.", severity=SEVERITY.MAJOR, src="REFL")
            return "unknown"

    @staticmethod
    def description(autosave_type):
        """
        Description for the autosaved type.
        Args:
            autosave_type: autosaved type

        Returns: description of the type

        """
        if autosave_type == AutosaveType.PARAM:
            return "beamline parameter"
        elif autosave_type == AutosaveType.VELOCITY:
            return "axis velocity"
        elif autosave_type == AutosaveType.MODE:
            return "beamline mode"
        else:
            print_and_log("Error: description requested for unknown autosave type.",
                          severity=SEVERITY.MAJOR, src="REFL")
            return ""


def read_autosave_value(value_id, autosave_type):
    """
    Try to read the autosaved setpoint value of a given parameter from file.

    Params:
        param_name (string): The name of the parameter

    Returns:
         The autosaved value for this parameter; None for no value
    """
    autosave = AutosaveFile(
        service_name="refl", file_name=AutosaveType.filename(autosave_type), folder=REFL_AUTOSAVE_PATH)
    return autosave.read_parameter(value_id, default=None)


def write_autosave_value(param_name, value, autosave_type):
    """
    Try to save the setpoint value of a given parameter to file.

    Params:
        param_name (string): The name of the parameter
        value: The value to save
    """
    autosave = AutosaveFile(
        service_name="refl", file_name=AutosaveType.filename(autosave_type), folder=REFL_AUTOSAVE_PATH)
    autosave.write_parameter(param_name, value)


def read_mode():
    """
    Read the last active mode from file.

    Returns:
        The name of the mode as string.
    """
    autosave = AutosaveFile(
        service_name="refl", file_name=AutosaveType.filename(AutosaveType.MODE), folder=REFL_AUTOSAVE_PATH)
    return autosave.read_parameter(MODE_KEY, default=None)


def save_mode(mode):
    """
    Save the current mode to file.

    Params:
        mode(str): The name of the mode to save.
    """
    autosave = AutosaveFile(
        service_name="refl", file_name=AutosaveType.filename(AutosaveType.MODE), folder=REFL_AUTOSAVE_PATH)
    autosave.write_parameter(MODE_KEY, value=mode)
