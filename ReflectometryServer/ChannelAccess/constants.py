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
