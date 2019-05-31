"""
constants for the reflecometry server.
"""
import os


def _get_env_var(name):
    return os.environ.get(name, "")


# Prefix for PVs on this instrument
MYPVPREFIX = _get_env_var('MYPVPREFIX')

# Prefix for all PVs in the server
REFLECTOMETRY_PREFIX = "{}REFL:".format(MYPVPREFIX)

# Reflectometry configuration file path
REFL_CONFIG_PATH = "{}".format(_get_env_var('ICPCONFIGROOT'))

# Reflectometry configuration file path
REFL_AUTOSAVE_PATH = os.path.join("{}".format(_get_env_var('ICPVARDIR')), "refl")

# alias motor DMOV values
MTR_MOVING = 0
MTR_STOPPED = 1
