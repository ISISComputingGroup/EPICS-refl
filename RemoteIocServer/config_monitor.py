from __future__ import print_function, unicode_literals, division

import json
import sys
import os

from genie_python.genie_cachannel_wrapper import CaChannelWrapper

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.channel_access import ChannelAccess
from server_common.utilities import print_and_log, dehex_and_decompress, waveform_to_string


class _ConfigurationMonitor(object):
    """
    Wrapper around an EPICS configuration monitor.
    """
    def __init__(self, pv):
        self._pv = pv

    def start(self, callback):
        ChannelAccess.add_monitor(self._pv, callback)

    def end(self):
        CaChannelWrapper.get_chan(self._pv).clear_channel()


class ConfigurationMonitor(object):
    """
    Monitors the configuration PV from whichever instrument is controlling this remote IOC.

    Calls back to the RemoteIocServer class on change of config.
    """
    def __init__(self, initial_remote_pv_prefix):
        self._monitor = None
        self.set_remote_pv_prefix(initial_remote_pv_prefix)

    def set_remote_pv_prefix(self, remote_pv_prefix):
        self._remote_pv_prefix = remote_pv_prefix
        self._start_monitoring()

    def _start_monitoring(self):
        """
        Monitors the PV and calls the provided callback function when the value changes
        """
        if self._monitor is not None:
            self._monitor.end()
        self._monitor = _ConfigurationMonitor("{}CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS".format(self._remote_pv_prefix))
        self._monitor.start(callback=_config_updated)


def _config_updated(value, alarm_severity, alarm_status):
    try:
        new_config = dehex_and_decompress(waveform_to_string(value))

        # Check it parses as JSON.
        json.loads(new_config)

        with open(os.path.join("C:\\", "Instrument", "a.txt"), "w") as f:
            f.write(new_config)
    except (TypeError, ValueError, IOError) as e:
        print_and_log("Config JSON from instrument not decoded correctly: {}: {}".format(e.__class__.__name__, e))
