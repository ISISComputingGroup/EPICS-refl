import logging
import os

from ReflectometryServer.ChannelAccess.constants import REFL_AUTOSAVE_PATH

logger = logging.getLogger(__name__)

PARAM_AUTOSAVE_PATH = os.path.join(REFL_AUTOSAVE_PATH, "params.txt")
MODE_AUTOSAVE_PATH = os.path.join(REFL_AUTOSAVE_PATH, "mode.txt")


def _format_param(param_name, value):
    """
    Format a parameter entry into a line containing a simple space separated key-value pair.

    Params:
        key (string): The name of the parameter
        value: The value to save

    Returns: A formatted string to write to file
    """
    return "{} {}\n".format(param_name, value)


def read_autosave_param(param_name):
    """
    Try to read the autosaved setpoint value of a given parameter from file.

    Params:
        param_name (string): The name of the parameter

    Returns: A formatted string to write to file
    """
    try:
        with open(PARAM_AUTOSAVE_PATH) as f:
            lines = f.readlines()
            for line in lines:
                key, val = line.split()
                if key.upper() == param_name.upper():
                    return val
        logger.info("No autosave value found for parameter {}".format(param_name))
    except Exception as e:
        logger.error("Failed to read autosave parameter {}: {}".format(param_name, e))
        return None


def write_autosave_param(param_name, value):
    """
    Try to save the setpoint value of a given parameter to file.

    Params:
        param_name (string): The name of the parameter
        value: The value to save

    Returns: A formatted string to write to file
    """
    if not os.path.exists(REFL_AUTOSAVE_PATH):
        os.makedirs(REFL_AUTOSAVE_PATH)
    try:
        if not os.path.exists(PARAM_AUTOSAVE_PATH):
            with open(PARAM_AUTOSAVE_PATH, "w") as f:
                f.writelines(_format_param(param_name, value))
                logger.info("Creating parameter autosave file.")
                logger.info("Parameter {} autosave value added: {}".format(param_name, value))
                return
        else:
            with open(PARAM_AUTOSAVE_PATH, "r") as f:
                lines = f.readlines()
            for index, line in enumerate(lines):
                key = line.split()[0]
                if key.upper() == param_name.upper():
                    lines[index] = _format_param(param_name, value)
                    logger.info("Parameter {} autosave value changed: {}".format(param_name, value))
                    break
            else:
                lines.append(_format_param(param_name, value))
                logger.info("Parameter {} autosave value added: {}".format(param_name, value))

            with open(PARAM_AUTOSAVE_PATH, "w+") as f:
                f.writelines(lines)

    except Exception as e:
        logger.error("Failed to write autosave parameter {}: {}".format(param_name, e))


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
        return None
