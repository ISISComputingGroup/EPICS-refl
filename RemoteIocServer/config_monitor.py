"""
Module to help monitor and react to the configuration on the instrument server.
"""
from __future__ import print_function, unicode_literals, division, absolute_import

import json
import zlib
import threading

import six

from BlockServer.config.configuration import Configuration
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from RemoteIocServer.utilities import print_and_log, get_hostname_from_prefix, THREADPOOL
from server_common.channel_access import ChannelAccess
from server_common.utilities import dehex_and_decompress_waveform
from BlockServer.config.ioc import IOC


REMOTE_IOC_CONFIG_NAME = "_REMOTE_IOC"

CONFIG_UPDATING_LOCK = threading.RLock()


def needs_config_updating_lock(func):
    """
    Add thread locking to this function to stop it being accessed in parallel
    Args:
        func: function to lock
    """
    @six.wraps(func)
    def _wrapper(*args, **kwargs):
        with CONFIG_UPDATING_LOCK:
            return func(*args, **kwargs)
    return _wrapper


class _EpicsMonitor(object):
    """
    Wrapper around an EPICS monitor.
    """
    def __init__(self, pv):
        """
        Initialise an epics monitor object without starting the monitor.

        Args:
            pv: the pv to monitor
        """
        self._pv = pv

    def start(self, callback):
        """
        Starts an EPICS monitor with the provided callback function on value.

        Args:
            callback (func): function to call on value change
        """
        ChannelAccess.add_monitor(self._pv, callback)

    def end(self):
        """
        Ends an EPICS monitor
        """
        ChannelAccess.clear_monitor(self._pv)


class ConfigurationMonitor(object):
    """
    Monitors the configuration PV from whichever instrument is controlling this remote IOC.

    Calls back to the RemoteIocServer class on change of config.
    """
    def __init__(self, local_pv_prefix, restart_iocs_callback):
        """
        Init.

        Args:
            local_pv_prefix: the local pv prefix
            restart_iocs_callback: callback function to call when pv value changes
        """
        self._monitor = None
        self._local_pv_prefix = local_pv_prefix
        self.restart_iocs_callback_func = restart_iocs_callback
        self._remote_hostname = None

        self._remote_pv_prefix = None
        self._remote_hostname = None
        self._file_manager = ConfigurationFileManager()

    def set_remote_pv_prefix(self, remote_pv_prefix):
        """
        Sets the remote PV prefix

        Args:
            remote_pv_prefix (str): the remote pv prefix
        """
        self._remote_pv_prefix = remote_pv_prefix
        self._remote_hostname = get_hostname_from_prefix(remote_pv_prefix)

        if self._remote_pv_prefix is None or self._remote_hostname is None:
            print_and_log("ConfigMonitor: prefix/hostname not set - will not monitor")
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """
        Monitors the PV and calls the provided callback function when the value changes
        """
        self._stop_monitoring()
        self._monitor = _EpicsMonitor("{}CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS".format(self._remote_pv_prefix))
        self._monitor.start(callback=self._config_updated)

    def _stop_monitoring(self):
        if self._monitor is not None:
            self._monitor.end()
        self._monitor = None

    @needs_config_updating_lock
    def _config_updated(self, value, *_, **__):
        try:
            new_config = dehex_and_decompress_waveform(value)
            self.write_new_config_as_xml(new_config)
            THREADPOOL.submit(self.restart_iocs_callback_func)
        except (TypeError, ValueError, IOError, zlib.error) as e:
            print_and_log("ConfigMonitor: Config JSON from instrument not decoded correctly: {}: {}"
                          .format(e.__class__.__name__, e))
            print_and_log("ConfigMonitor: Raw PV value was: {}".format(value))

    @needs_config_updating_lock
    def write_new_config_as_xml(self, config_json_as_str):
        """
        Write new config files for the remote IOC configuration based on configuration json for a blockserver config pv.
        This uses just those IOCs on this remote server that are referred to as being remote in the blockserver config.

        Args:
            config_json_as_str: remote configuration on which to base the xml
        """
        print_and_log("ConfigMonitor: Got new config monitor, writing new config files")
        config_json = json.loads(config_json_as_str, "ascii")

        config = self._create_config_from_instrument_config(config_json)

        self._file_manager.save_config(config, False)
        self._update_last_config()

        print_and_log("ConfigMonitor: Finished writing new config")

    def _create_config_from_instrument_config(self, config_from_json):

        config = Configuration({})
        config.set_name(REMOTE_IOC_CONFIG_NAME)
        config.meta.description = "Configuration for remote IOC"

        iocs_list = []

        if "component_iocs" in config_from_json and config_from_json["component_iocs"] is not None:
            for ioc in config_from_json["component_iocs"]:
                if ioc["remotePvPrefix"] == self._local_pv_prefix:  # If the IOC is meant to run on this machine...
                    iocs_list.append(ioc)

        if "iocs" in config_from_json and config_from_json["iocs"] is not None:
            for ioc in config_from_json["iocs"]:
                if ioc["remotePvPrefix"] == self._local_pv_prefix:  # If the IOC is meant to run on this machine...
                    iocs_list.append(ioc)

        iocs = {}
        for ioc in iocs_list:
            name = ioc["name"]
            macros = {macro["name"]: {"name": macro["name"], "value": macro["value"]} for macro in ioc["macros"]}
            macros["ACF_IH1"] = {"name": "ACF_IH1", "value": self._remote_hostname}
            try:
                iocs[name.upper()] = IOC(
                    name=name,
                    autostart=ioc["autostart"],
                    restart=ioc["restart"],
                    component=None,  # We don't care what component it was defined in.
                    macros=macros,
                    pvsets={pvset["name"]: {"name": pvset["name"], "value": pvset["value"]} for pvset in ioc["pvsets"]},
                    pvs={pv["name"]: {"name": pv["name"], "value": pv["value"]} for pv in ioc["pvs"]},
                    simlevel=ioc["simlevel"],
                    remotePvPrefix=ioc["remotePvPrefix"],
                )
            except KeyError:
                print_and_log("ConfigMonitor: not all attributes could be extracted from config."
                              "The config may not have been updated to the correct schema. Ignoring this IOC.")

        config.iocs = iocs

        return config

    @needs_config_updating_lock
    def _update_last_config(self):
        print_and_log("ConfigMonitor: Writing last_config.txt")
        with open(FILEPATH_MANAGER.get_last_config_file_path(), "w") as f:
            f.write("{}\n".format(REMOTE_IOC_CONFIG_NAME))
