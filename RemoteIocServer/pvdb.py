from __future__ import print_function, unicode_literals, division, absolute_import
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import char_waveform


class PvNames(object):
    INSTRUMENT = "INSTRUMENT"
    INSTRUMENT_SP = "INSTRUMENT:SP"


STATIC_PV_DATABASE = {
    PvNames.INSTRUMENT: char_waveform(50),
    PvNames.INSTRUMENT_SP: char_waveform(50),
}
