"""
constants for the reflectometry server.
"""
import os


def _get_env_var(name):
    return os.environ.get(name, "")


# Prefix for PVs on this instrument
MYPVPREFIX = _get_env_var('MYPVPREFIX')

IOC_DIR = _get_env_var('MYDIRBLOCK')

REFL_IOC_NAME = "REFL_01"

# Prefix for all PVs in the server
REFLECTOMETRY_PREFIX = "{}{}:".format(MYPVPREFIX, REFL_IOC_NAME)

# Reflectometry configuration file path
REFL_CONFIG_PATH = os.path.abspath(os.path.join("{}".format(_get_env_var('ICPCONFIGROOT')), "refl"))

# Reflectometry configuration file path
REFL_AUTOSAVE_PATH = os.path.join("{}".format(_get_env_var('ICPVARDIR')), "refl")

# Path to security access rules file
DEFAULT_ASG_RULES = os.path.join("{}".format(
    os.environ.get('KIT_ROOT', os.path.join('C:\Instrument', 'Apps', 'EPICS'))),
    "support", "AccessSecurity", "master", "default.acf")

# alias motor DMOV values
MTR_MOVING = 0
MTR_STOPPED = 1
