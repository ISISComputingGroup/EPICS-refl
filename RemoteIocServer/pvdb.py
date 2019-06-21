from __future__ import print_function, unicode_literals, division
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import char_waveform


class PvNames(object):
    INSTRUMENT = "INSTRUMENT"
    INSTRUMENT_SP = "INSTRUMENT:SP"
    READ_GLOBALS = "GLOBALMACROS"
    WRITE_GLOBALS = "GLOBALMACROS:SP"


STATIC_PV_DATABASE = {
    PvNames.INSTRUMENT: char_waveform(50),
    PvNames.INSTRUMENT_SP: char_waveform(50),
    PvNames.READ_GLOBALS: char_waveform(16000),
    PvNames.WRITE_GLOBALS: char_waveform(16000),
}


def pvdb_for_ioc(iocname):
    return {
        "{}:START".format(iocname): {'type': 'int'},
        "{}:STOP".format(iocname): {'type': 'int'},
        "{}:RESTART".format(iocname): {'type': 'int'},
    }
