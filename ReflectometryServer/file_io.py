"""
file io for various autosave and other parts of the system
"""

import logging

from server_common.autosave import (
    AutosaveFile,
    BoolConversion,
    FloatConversion,
    OptionalIntConversion,
    StringConversion,
)

from ReflectometryServer.ChannelAccess.constants import REFL_AUTOSAVE_PATH
from ReflectometryServer.geometry import PositionAndAngle

logger = logging.getLogger(__name__)

PARAM_AUTOSAVE_FILE = "params"
VELOCITY_AUTOSAVE_FILE = "velocity"
MODE_AUTOSAVE_FILE = "mode"
DISABLE_MODE_AUTOSAVE_FILE = "disable_mode_incoming_beams"
COMPONENT_AUTOSAVE_FILE = "component"

MODE_KEY = "mode"

# the mode autosave service
mode_autosave = AutosaveFile(
    service_name="refl", file_name=MODE_AUTOSAVE_FILE, folder=REFL_AUTOSAVE_PATH
)

# the disable mode autosave service
disable_mode_autosave = AutosaveFile(
    service_name="refl",
    file_name=DISABLE_MODE_AUTOSAVE_FILE,
    conversion=PositionAndAngle,
    folder=REFL_AUTOSAVE_PATH,
)

# the parameter autosave service for floats
param_float_autosave = AutosaveFile(
    service_name="refl",
    file_name=PARAM_AUTOSAVE_FILE,
    conversion=FloatConversion,
    folder=REFL_AUTOSAVE_PATH,
)

# the parameter autosave service for booleans
param_bool_autosave = AutosaveFile(
    service_name="refl",
    file_name=PARAM_AUTOSAVE_FILE,
    conversion=BoolConversion,
    folder=REFL_AUTOSAVE_PATH,
)

# the parameter autosave service for strings
param_string_autosave = AutosaveFile(
    service_name="refl",
    file_name=PARAM_AUTOSAVE_FILE,
    conversion=StringConversion,
    folder=REFL_AUTOSAVE_PATH,
)

# the velocity autosave service for floats
velocity_float_autosave = AutosaveFile(
    service_name="refl",
    file_name=VELOCITY_AUTOSAVE_FILE,
    conversion=FloatConversion,
    folder=REFL_AUTOSAVE_PATH,
)

# the velocity autosave service for booleans
velocity_bool_autosave = AutosaveFile(
    service_name="refl",
    file_name=VELOCITY_AUTOSAVE_FILE,
    conversion=BoolConversion,
    folder=REFL_AUTOSAVE_PATH,
)

parking_index_autosave = AutosaveFile(
    service_name="refl",
    file_name=COMPONENT_AUTOSAVE_FILE,
    conversion=OptionalIntConversion,
    folder=REFL_AUTOSAVE_PATH,
)
