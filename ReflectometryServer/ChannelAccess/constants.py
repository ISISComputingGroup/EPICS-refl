"""
constants for the reflecometry server.
"""
import os


def _get_env_var(name):
    return os.environ.get(name, "")


# Prefix for all PVs in the server
REFLECTOMETRY_PREFIX = "{}REFL:".format(_get_env_var('MYPVPREFIX'))
