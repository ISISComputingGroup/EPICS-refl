"""
file io for various autosave and other parts of the system
"""

import logging
import os

from enum import Enum
from ReflectometryServer.ChannelAccess.constants import REFL_AUTOSAVE_PATH
from server_common.utilities import print_and_log, SEVERITY

logger = logging.getLogger(__name__)

PARAM_AUTOSAVE_PATH = os.path.join(REFL_AUTOSAVE_PATH, "params.txt")
VELOCITY_AUTOSAVE_PATH = os.path.join(REFL_AUTOSAVE_PATH, "velocity.txt")
MODE_AUTOSAVE_PATH = os.path.join(REFL_AUTOSAVE_PATH, "mode.txt")


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
    def path(autosave_type):
        """
        Path for file that autosave type is saved into.
        Args:
            autosave_type: autosave type

        Returns: path to file
        """
        if autosave_type == AutosaveType.PARAM:
            return PARAM_AUTOSAVE_PATH
        elif autosave_type == AutosaveType.VELOCITY:
            return VELOCITY_AUTOSAVE_PATH
        elif autosave_type == AutosaveType.MODE:
            return MODE_AUTOSAVE_PATH
        else:
            print_and_log("Error: file path requested for unknown autosave type.", severity=SEVERITY.MAJOR, src="REFL")
            return ""

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


def _format_autosave(key, value):
    """
    Format a parameter entry into a line containing a simple space separated key-value pair.

    Params:
        key (string): The name of the parameter
        value: The value to save

    Returns:
         A formatted string to write to file
    """
    return "{} {}\n".format(key, value)


def read_autosave_value(value_id, autosave_type):
    """
    Try to read the autosaved setpoint value of a given parameter from file.

    Params:
        param_name (string): The name of the parameter

    Returns:
         The autosaved value for this parameter; None for no value
    """
    autosave_file_path = AutosaveType.path(autosave_type)
    type_desc = AutosaveType.description(autosave_type)
    try:
        with open(autosave_file_path) as f:
            lines = f.readlines()
            for line in lines:
                # Split the line into a key and string value pair (where the string is a single value or list)
                key, val = line.split(" ", 1)
                if key.upper() == value_id.upper():
                    return val
        logger.info("No autosave value found for key {} (type: {})".format(value_id, type_desc))
    except Exception as e:
        logger.error("Failed to read autosave value for key {} (type: {}): {}".format(value_id, type_desc, e))
        return None


def write_autosave_value(param_name, value, autosave_type):
    """
    Try to save the setpoint value of a given parameter to file.

    Params:
        param_name (string): The name of the parameter
        value: The value to save
    """
    if not os.path.exists(REFL_AUTOSAVE_PATH):
        os.makedirs(REFL_AUTOSAVE_PATH)
    autosave_file_path = AutosaveType.path(autosave_type)
    type_desc = AutosaveType.description(autosave_type)
    try:
        if not os.path.exists(autosave_file_path):
            with open(autosave_file_path, "w") as f:
                f.writelines(_format_autosave(param_name, value))
                logger.info("Creating {} autosave file.".format(type_desc))
                logger.info("Autosave value added for key {} (type: {}): {}".format(param_name, type_desc, value))
                return
        else:
            with open(autosave_file_path, "r") as f:
                lines = f.readlines()
            for index, line in enumerate(lines):
                key = line.split()[0]
                if key.upper() == param_name.upper():
                    lines[index] = _format_autosave(param_name, value)
                    logger.info("Autosave value changed for key {} (type: {}): {}".format(param_name, type_desc, value))
                    break
            else:
                lines.append(_format_autosave(param_name, value))
                logger.info("Autosave value added for key {} (type: {}): {}".format(param_name, type_desc, value))

            with open(autosave_file_path, "w+") as f:
                f.writelines(lines)

    except Exception as e:
        logger.error("Failed to write autosave value for {} (type: {}): {}".format(param_name, type_desc, e))


def read_mode():
    """
    Read the last active mode from file.

    Returns:
        The name of the mode as string.
    """
    try:
        with open(MODE_AUTOSAVE_PATH) as f:
            return f.readlines()[0]
    except Exception as e:
        logger.error("Failed to read mode: {}".format(e))
        return None


def save_mode(mode):
    """
    Save the current mode to file.

    Params:
        mode(str): The name of the mode to save.
    """
    if not os.path.exists(REFL_AUTOSAVE_PATH):
        os.makedirs(REFL_AUTOSAVE_PATH)
    try:
        with open(MODE_AUTOSAVE_PATH, "w") as f:
            f.write(mode)
    except Exception as e:
        logger.error("Failed to save mode: {}".format(e))
