import os


def _get_env_var(name):
    try:
        return os.environ[name]
    except:
        return ""

MACROS = {
    "$(MYPVPREFIX)": _get_env_var('MYPVPREFIX'),
    "$(EPICS_KIT_ROOT)": _get_env_var('EPICS_KIT_ROOT'),
    "$(ICPCONFIGROOT)": _get_env_var('ICPCONFIGROOT'),
    "$(ICPVARDIR)": _get_env_var('ICPVARDIR')
}

REFLECTOMETRY_PREFIX = MACROS["$(MYPVPREFIX)"] + "REFL:"
PVPREFIX_MACRO = "$(MYPVPREFIX)"
