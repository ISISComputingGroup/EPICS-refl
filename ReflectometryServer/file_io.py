import logging
import os

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH

logger = logging.getLogger(__name__)

AUTOSAVE_FILE_PATH = os.path.join(REFL_CONFIG_PATH, "refl", "params.txt")


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
        with open(AUTOSAVE_FILE_PATH) as f:
            lines = f.readlines()
            for line in lines:
                key, val = line.split()
                if key == param_name:
                    return val
        logger.info("No autosave value found for parameter {}".format(param_name))
    except Exception as e:
        logger.error("Failed to read autosave parameter {}: {}".format(param_name, e.message))
        return None


def write_autosave_param(param_name, value):
    """
    Try to save the setpoint value of a given parameter to file.

    Params:
        param_name (string): The name of the parameter
        value: The value to save

    Returns: A formatted string to write to file
    """
    try:
        if not os.path.exists(AUTOSAVE_FILE_PATH):
            with open(AUTOSAVE_FILE_PATH, "w") as f:
                f.writelines(_format_param(param_name, value))

                return
        else:
            with open(AUTOSAVE_FILE_PATH, "r") as f:
                lines = f.readlines()
                logger.info("Creating parameter autosave file.")
                logger.info("Parameter {} autosave value added: {}".format(param_name, value))
            with open(AUTOSAVE_FILE_PATH, "w+") as f:
                for i in range(len(lines)):
                    key = lines[i].split()[0]
                    if key == param_name:
                        lines[i] = _format_param(param_name, value)
                        f.writelines(lines)
                        logger.info("Parameter {} autosave value changed: {}".format(param_name, value))
                        return
                lines.append(_format_param(param_name, value))
                f.writelines(lines)
                logger.info("Parameter {} autosave value added: {}".format(param_name, value))
    except Exception as e:
        logger.error("Failed to write autosave parameter {}: {}".format(param_name, e.message))
