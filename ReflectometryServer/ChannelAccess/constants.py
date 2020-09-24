"""
constants for the reflectometry server.
"""
import os


def _get_env_var(name):
    return os.environ.get(name, "")


# Prefix for PVs on this instrument
MYPVPREFIX = _get_env_var('MYPVPREFIX')

REFL_IOC_NAME = "REFL_01"

# Prefix for all PVs in the server
REFLECTOMETRY_PREFIX = "{}{}:".format(MYPVPREFIX, REFL_IOC_NAME)

# Reflectometry configuration file path
REFL_CONFIG_PATH = os.path.abspath(os.path.join("{}".format(_get_env_var('ICPCONFIGROOT')), "refl"))

# Reflectometry configuration file path
REFL_AUTOSAVE_PATH = os.path.join("{}".format(_get_env_var('ICPVARDIR')), "refl")

# Path to security access rules file
DEFAULT_ASG_RULES = os.path.join("{}".format(
    os.environ.get('KIT_ROOT', os.path.join(r'C:\Instrument', 'Apps', 'EPICS'))),
    "support", "AccessSecurity", "master", "default.acf")

# alias motor DMOV values
MTR_MOVING = 0
MTR_STOPPED = 1

# PV to set that reflectometry calculation is not complete, i.e. it still considered that motors are moving
MOTOR_MOVING_PV = "{}CS:MOT:_MOVING2.A".format(MYPVPREFIX)

# maximum allowable alarm value
MAX_ALARM_ID = 15

# standard field for float pvs
STANDARD_FLOAT_PV_FIELDS = {'type': 'float', 'prec': 3, 'value': 0.0}
