from __future__ import print_function, unicode_literals, division, absolute_import

import json
import os
import zlib
import threading

import six

from RemoteIocServer.utilities import print_and_log, get_hostname_from_prefix, THREADPOOL
from server_common.channel_access import ChannelAccess
from genie_python.genie_cachannel_wrapper import CaChannelWrapper
from genie_python.channel_access_exceptions import UnableToConnectToPVException
from server_common.utilities import dehex_and_decompress, waveform_to_string
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.config.ioc import IOC


REMOTE_IOC_CONFIG_NAME = "_REMOTE_IOC"

EMPTY_COMPONENTS_XML = """<?xml version="1.0" ?>
<components xmlns="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:comp="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>
"""

EMPTY_GROUPS_XML = """<?xml version="1.0" ?>
<groups xmlns="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:grp="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>
"""

EMPTY_BLOCKS_XML = """<?xml version="1.0" ?>
<blocks xmlns="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:blk="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"></blocks>
"""

META_XML = """<?xml version="1.0" ?>
<meta>
    <description>Configuration for remote IOC</description>
    <synoptic>-- NONE --</synoptic>
    <edits></edits>
</meta>
"""


CONFIG_UPDATING_LOCK = threading.RLock()


def needs_config_updating_lock(func):
    @six.wraps(func)
    def wrapper(*args, **kwargs):
        with CONFIG_UPDATING_LOCK:
            return func(*args, **kwargs)
    return wrapper


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
        try:
            CaChannelWrapper.get_chan(self._pv).clear_channel()
        except UnableToConnectToPVException:
            pass


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
            new_config = dehex_and_decompress(waveform_to_string(value))
            self._write_new_config_as_xml(new_config)
            THREADPOOL.submit(self.restart_iocs_callback_func)
        except (TypeError, ValueError, IOError, zlib.error) as e:
            print_and_log("ConfigMonitor: Config JSON from instrument not decoded correctly: {}: {}"
                          .format(e.__class__.__name__, e))
            print_and_log("ConfigMonitor: Raw PV value was: {}".format(value))

    @needs_config_updating_lock
    def _write_new_config_as_xml(self, config_json):
        print_and_log("ConfigMonitor: Got new config monitor, writing new config files")
        config = json.loads(config_json, "ascii")

        config_base = os.path.normpath(os.getenv("ICPCONFIGROOT"))
        config_dir = os.path.join(config_base, "configurations", REMOTE_IOC_CONFIG_NAME)

        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        self._write_iocs_xml(config_dir, config)
        self._write_standard_config_files(config_dir)
        self._update_last_config(config_base)

        print_and_log("ConfigMonitor: Finished writing new config")

    @needs_config_updating_lock
    def _write_iocs_xml(self, config_dir, config):
        iocs_list = []

        if "component_iocs" in config and config["component_iocs"] is not None:
            for ioc in config["component_iocs"]:
                if ioc["remotePvPrefix"] == self._local_pv_prefix:  # If the IOC is meant to run on this machine...
                    iocs_list.append(ioc)

        if "iocs" in config and config["iocs"] is not None:
            for ioc in config["iocs"]:
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

        iocs_xml = ConfigurationXmlConverter.iocs_to_xml(iocs)

        print_and_log("ConfigMonitor: Writing iocs.xml")
        with open(os.path.join(config_dir, "iocs.xml"), "w") as f:
            f.write(str(iocs_xml))

    @needs_config_updating_lock
    def _write_standard_config_files(self, config_dir):
        print_and_log("ConfigMonitor: Writing components.xml")
        with open(os.path.join(config_dir, "components.xml"), "w") as f:
            f.write(EMPTY_COMPONENTS_XML)

        print_and_log("ConfigMonitor: Writing blocks.xml")
        with open(os.path.join(config_dir, "blocks.xml"), "w") as f:
            f.write(EMPTY_BLOCKS_XML)

        print_and_log("ConfigMonitor: Writing groups.xml")
        with open(os.path.join(config_dir, "groups.xml"), "w") as f:
            f.write(EMPTY_GROUPS_XML)

        print_and_log("ConfigMonitor: Writing meta.xml")
        with open(os.path.join(config_dir, "meta.xml"), "w") as f:
            f.write(META_XML)

    @needs_config_updating_lock
    def _update_last_config(self, config_base):
        print_and_log("ConfigMonitor: Writing last_config.txt")
        with open(os.path.join(config_base, "last_config.txt"), "w") as f:
            f.write("{}\n".format(REMOTE_IOC_CONFIG_NAME))
