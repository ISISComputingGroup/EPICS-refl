# Add root path for access to server_commons
import os
import sys
sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))


# Standard imports
from pcaspy import Driver
import argparse
import json
from threading import Thread, RLock
from time import sleep
from gateway import Gateway
from active_config_server import ActiveConfigServerManager
from config_server import ConfigServerManager
from server_common.channel_access_server import CAServer
from server_common.utilities import compress_and_hex, dehex_and_decompress, print_and_log
from macros import MACROS, BLOCKSERVER_PREFIX
from all_configs_list import ConfigListManager
from config.file_watcher_manager import ConfigFileWatcherManager

# For documentation on these commands see the accompanying block_server.rst file
PVDB = {
    'BLOCKNAMES': {
        'type': 'char',
        'count': 16000,
    },
    'BLOCK_DETAILS': {
        'type': 'char',
        'count': 16000,
    },
    'GROUPS': {
        'type': 'char',
        'count': 16000,
    },
    'ADD_BLOCKS': {
        'type': 'char',
        'count': 16000,
    },
    'REMOVE_BLOCKS': {
        'type': 'char',
        'count': 16000,
    },
    'EDIT_BLOCKS': {
        'type': 'char',
        'count': 16000,
    },
    'ADD_COMPS': {
        'type': 'char',
        'count': 1000,
    },
    'REMOVE_COMPS': {
        'type': 'char',
        'count': 1000,
    },
    'COMPS': {
        'type': 'char',
        'count': 16000,
    },
    'LOAD_CONFIG': {
        'type': 'char',
        'count': 1000,
    },
    'SAVE_CONFIG': {
        'type': 'char',
        'count': 1000,
    },
    'LOAD_COMP': {
        'type': 'char',
        'count': 1000,
    },
    'SAVE_COMP': {
        'type': 'char',
        'count': 1000,
    },
    'CLEAR_CONFIG': {
        'type': 'char',
        'count': 100,
    },
    'CONFIG': {
        'type': 'char',
        'count': 1000,
    },
    'ACTION_CHANGES': {
        'type': 'char',
        'count': 100,
    },
    'SET_GROUPS': {
        'type': 'char',
        'count': 16000,
    },
    'START_IOCS': {
        'type': 'char',
        'count': 16000,
    },
    'STOP_IOCS': {
        'type': 'char',
        'count': 1000,
    },
    'RESTART_IOCS': {
        'type': 'char',
        'count': 1000,
    },
    'ADD_IOCS': {
        'type': 'char',
        'count': 1000,
    },
    'REMOVE_IOCS': {
        'type': 'char',
        'count': 1000,
    },
    'CONFIG_IOCS': {
        'type': 'char',
        'count': 16000,
    },
    'CONFIG_COMPS': {
        'type': 'char',
        'count': 16000,
    },
    'CONFIGS': {
        'type': 'char',
        'count': 16000,
    },
    'GET_RC_OUT': {
        'type': 'char',
        'count': 16000,
    },
    'GET_RC_PARS': {
        'type': 'char',
        'count': 16000,
    },
    'SET_RC_PARS': {
        'type': 'char',
        'count': 16000,
    },
    'GET_CURR_CONFIG_DETAILS': {
        'type': 'char',
        'count': 64000,
    },
    'SET_CURR_CONFIG_DETAILS': {
        'type': 'char',
        'count': 64000,
    },
    'SAVE_NEW_CONFIG': {
        'type': 'char',
        'count': 64000,
    },
    'SAVE_NEW_COMPONENT': {
        'type': 'char',
        'count': 64000,
    },
    'SERVER_STATUS': {
        'type': 'char',
        'count': 1000,
    },
    'DELETE_CONFIGS': {
        'type': 'char',
        'count': 64000,
    },
    'DELETE_COMPONENTS': {
        'type': 'char',
        'count': 64000,
    },
    'BLANK_CONFIG': {
        'type': 'char',
        'count': 64000,
    },
    'CURR_CONFIG_CHANGED': {
        'type': 'int'
    },
    'ACK_CURR_CHANGED': {
        'type': 'int'
    }
}


class BlockServer(Driver):
    def __init__(self, ca_server):
        super(BlockServer, self).__init__()
        self._gateway = Gateway(GATEWAY_PREFIX, BLOCK_PREFIX,  PVLIST_FILE)
        self._active_configserver = None
        self._status = "INITIALISING"

        # Import data about all configs
        try:
            self._config_list = ConfigListManager(self, CONFIG_DIR, ca_server, SCHEMA_DIR)
        except Exception as err:
            print_and_log("Error creating inactive config list: " + str(err), "ERROR")

        # Threading stuff
        self.monitor_lock = RLock()
        self.write_lock = RLock()
        self.write_queue = list()

        # Start a background thread for keeping track of running IOCs
        monitor_thread = Thread(target=self.update_ioc_monitors, args=())
        monitor_thread.daemon = True  # Daemonise thread
        monitor_thread.start()

        # Start a background thread for handling write commands
        write_thread = Thread(target=self.consume_write_queue, args=())
        write_thread.daemon = True  # Daemonise thread
        write_thread.start()

        # Start file watcher
        self._filewatcher = ConfigFileWatcherManager(CONFIG_DIR, SCHEMA_DIR, self._config_list)

        with self.write_lock:
            self.write_queue.append((self.initialise_configserver, (), "INITIALISING"))

    def initialise_configserver(self):
        # This is in a seperate method so it can be sent to the thread queue
        self._active_configserver = ActiveConfigServerManager(CONFIG_DIR, MACROS, ARCHIVE_UPLOADER, ARCHIVE_SETTINGS,
                                                              BLOCK_PREFIX)
        try:
            if self._gateway.exists():
                print_and_log("Found gateway")
                self.load_last_config()
            else:
                print_and_log("Could not connect to gateway - is it running?")
                self.load_last_config()
        except Exception as err:
            print_and_log("Could not load last configuration. Message was: %s" % err, "ERROR")
            self._active_configserver.clear_config()

        # Update monitors to current values
        self.update_blocks_monitors()
        self.update_config_monitors()

    def read(self, reason):
        # This is called by CA
        try:
            if reason == 'BLOCKNAMES':
                value = compress_and_hex(self._active_configserver.get_blocknames_json())
            elif reason == 'GROUPS':
                value = compress_and_hex(self._active_configserver.get_groupings_json())
            elif reason == 'CONFIG':
                value = compress_and_hex(self._active_configserver.get_config_name_json())
            elif reason == 'CONFIG_IOCS':
                value = compress_and_hex(self._active_configserver.get_config_iocs_json())
            elif reason == 'CONFIGS':
                value = compress_and_hex(self._config_list.get_configs_json())
            elif reason == 'CONFIG_COMPS':
                value = compress_and_hex(self._active_configserver.get_conf_subconfigs_json())
            elif reason == 'COMPS':
                value = compress_and_hex(self._config_list.get_subconfigs_json())
            elif reason == 'GET_RC_OUT':
                value = compress_and_hex(self._active_configserver.get_out_of_range_pvs())
            elif reason == 'GET_RC_PARS':
                value = compress_and_hex(self._active_configserver.get_runcontrol_settings_json())
            elif reason == "GET_CURR_CONFIG_DETAILS":
                value = compress_and_hex(self._active_configserver.get_config_details())
            elif reason == "SERVER_STATUS":
                value = compress_and_hex(self.get_server_status())
            elif reason == "BLANK_CONFIG":
                value = compress_and_hex(self.get_blank_config())
            elif reason == "CURR_CONFIG_CHANGED":
                value = self._config_list.get_active_changed()
            else:
                value = self.getParam(reason)
        except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        return value

    def write(self, reason, value):
        # This is called by CA
        # All write commands are queued as CA is single-threaded
        status = True
        if reason == 'ADD_BLOCKS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.add_blocks_json(data)
                self.update_blocks_monitors()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'REMOVE_BLOCKS':
            try:
                self._active_configserver.remove_blocks(dehex_and_decompress(value))
                self.update_blocks_monitors()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'EDIT_BLOCKS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.edit_blocks_json(data)
                self.update_blocks_monitors()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'ADD_COMPS':
            try:
                data = dehex_and_decompress(value)
                self.add_active_subconfigs(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'REMOVE_COMPS':
            try:
                data = dehex_and_decompress(value)
                self.remove_active_subconfigs(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'LOAD_CONFIG':
            try:
                with self.write_lock:
                    self.write_queue.append((self.load_config, (value,), "LOADING_CONFIG"))
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SAVE_CONFIG':
            try:
                data = dehex_and_decompress(value)
                self.save_active_config(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'LOAD_COMP':
            try:
                with self.write_lock:
                    self.write_queue.append((self.load_config, (value, True), "LOADING_COMP"))
                self.update_blocks_monitors()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SAVE_COMP':
            try:
                data = dehex_and_decompress(value)
                self.save_active_as_subconfig(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex("Error: " + str(err))
                print_and_log(str(err), "ERROR")
        elif reason == 'CLEAR_CONFIG':
            try:
                self._active_configserver.clear_config()
                self._initialise_config()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'ACTION_CHANGES':
            try:
                self.autosave_active_config()
                self._gateway.set_new_aliases(self._active_configserver.get_blocks())
                self._active_configserver.update_archiver()
                self._active_configserver.create_runcontrol_pvs()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SET_GROUPS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.set_groupings_json(data)
                self.update_blocks_monitors()
                self.autosave_active_config()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'START_IOCS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.start_iocs(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'STOP_IOCS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.stop_iocs(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'RESTART_IOCS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.restart_iocs(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'ADD_IOCS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.add_iocs(data)
                self.autosave_active_config()
                self.update_config_iocs_monitors()
                # Should we start the IOC?
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'REMOVE_IOCS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.remove_iocs(data)
                self.autosave_active_config()
                self.update_config_iocs_monitors()
                # Should we stop the IOC?
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SET_RC_PARS':
            try:
                data = dehex_and_decompress(value)
                self._active_configserver.set_runcontrol_settings_json(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SET_CURR_CONFIG_DETAILS':
            try:
                data = dehex_and_decompress(value).strip('"')
                self._active_configserver.set_config_details(data)
                self.save_active_config(self._active_configserver.get_config_name_json())
                self._initialise_config()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SAVE_NEW_CONFIG':
            try:
                data = dehex_and_decompress(value).strip('"')
                self.save_inactive_config(data)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'SAVE_NEW_COMPONENT':
            try:
                data = dehex_and_decompress(value).strip('"')
                self.save_inactive_config(data, True)
                self.update_comp_monitor()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'DELETE_CONFIGS':
            try:
                data = dehex_and_decompress(value).strip('"')
                self._config_list.delete_configs_json(data)
                self.update_config_monitors()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'DELETE_COMPONENTS':
            try:
                data = dehex_and_decompress(value).strip('"')
                self._config_list.delete_configs_json(data, True)
                self.update_comp_monitor()
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        elif reason == 'ACK_CURR_CHANGED':
            try:
                self._config_list.set_active_changed(False)
                value = compress_and_hex(json.dumps("OK"))
            except Exception as err:
                value = compress_and_hex(json.dumps("Error: " + str(err)))
                print_and_log(str(err), "ERROR")
        else:
            status = False
        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def load_last_config(self):
        last = self._active_configserver.load_last_config()
        if last is None:
            print_and_log("Could not retrieve last configuration - starting blank configuration")
            self._active_configserver.clear_config()
        else:
            print_and_log("Loaded last configuration: %s" % last)
        self._initialise_config()

    def _initialise_config(self, restart_iocs=True, init_gateway=True):
        # First stop all IOCS, then start the ones for the config
        # TODO: Should we stop all configs?
        if restart_iocs:
            self._active_configserver.stop_iocs_and_start_config_iocs()
        # Set up the gateway
        if init_gateway:
            self._gateway.set_new_aliases(self._active_configserver.get_blocks())
        self._config_list.active_config_name = self._active_configserver.get_config_name()
        self._config_list.active_components = self._active_configserver.get_conf_subconfigs()
        self.update_blocks_monitors()
        self.update_config_monitors()
        self.update_config_iocs_monitors()
        self.update_get_details_monitors()
        self._active_configserver.update_archiver()

    def load_config(self, value, is_subconfig=False):
        try:
            config = dehex_and_decompress(value)
            if is_subconfig:
                print_and_log("Loading sub-configuration: %s" % config)
                self._active_configserver.load_config(config, True)
            else:
                print_and_log("Loading configuration: %s" % config)
                self._active_configserver.load_config(config)
            # If we get this far then assume the config is okay
            self._initialise_config()
        except Exception as err:
            print_and_log(str(err), "ERROR")

    def add_active_subconfigs(self, config):
        # When adding a subconfig the IOCs in it are started
        self._active_configserver.add_subconfigs(config)
        # We need to refresh the gateway
        self._initialise_config(False, True)

    def remove_active_subconfigs(self, config):
        # When removing a subconfig we need to refresh the gateway
        self._active_configserver.remove_subconfigs(config)
        self._initialise_config(False, True)

    def save_inactive_config(self, json_data, as_subconfig=False):
        inactive = ConfigServerManager(CONFIG_DIR, MACROS)
        inactive.set_config_details(json_data)
        config_name = inactive.get_config_name()
        self._check_config_inactive(config_name, as_subconfig)
        self._filewatcher.pause()
        try:
            if not as_subconfig:
                print_and_log("Saving configuration: %s" % config_name)
                inactive.save_config()
                self._config_list.update_a_config_in_list(inactive)
                self.update_config_monitors()
            else:
                print_and_log("Saving sub-configuration: %s" % config_name)
                inactive.save_as_subconfig()
                self._config_list.update_a_config_in_list(inactive, True)
                self.update_comp_monitor()
        finally:
            self._filewatcher.resume()

    def save_active_config(self, json_name):
        self._filewatcher.pause()
        try:
            name = json.loads(json_name)
            print_and_log("Saving active configuration as: %s" % name)
            self._active_configserver.save_config(json_name)
            self._config_list.update_a_config_in_list(self._active_configserver)
            self.update_config_monitors()
        finally:
            self._filewatcher.resume()

    def save_active_as_subconfig(self, json_name):
        self._filewatcher.pause()
        try:
            name = json.loads(json_name)
            print_and_log("Trying to save active configuration as sub-configuration: %s" % name)
            self._active_configserver.save_as_subconfig(json_name)
            self._config_list.update_a_config_in_list(self._active_configserver, True)
            self.update_comp_monitor()
        finally:
            self._filewatcher.resume()

    def autosave_active_config(self):
        self._active_configserver.autosave_config()

    def update_blocks_monitors(self):
        with self.monitor_lock:
            # Blocks
            self.setParam("BLOCKNAMES", compress_and_hex(self._active_configserver.get_blocknames_json()))
            # Groups
            # Update the PV, so that groupings are updated for any CA monitors
            self.setParam("GROUPS", compress_and_hex(self._active_configserver.get_groupings_json()))
            # Update them
            self.updatePVs()

    def update_config_monitors(self):
        with self.monitor_lock:
            # set the config name
            self.setParam("CONFIG", compress_and_hex(self._active_configserver.get_config_name_json()))
            # set the available configs
            self.setParam("CONFIGS", compress_and_hex(self._config_list.get_configs_json()))
            # Update them
            self.updatePVs()

    def update_comp_monitor(self):
        with self.monitor_lock:
            self.setParam("COMPS", compress_and_hex(self._config_list.get_subconfigs_json()))
            # Update them
            self.updatePVs()

    def update_changed_monitor(self):
        with self.monitor_lock:
            self.setParam("CURR_CONFIG_CHANGED", self._config_list.get_active_changed())
            self.updatePVs()

    def update_ioc_monitors(self):
        while True:
            if self._active_configserver is not None:
                with self.monitor_lock:
                    self.setParam("CONFIG_IOCS", compress_and_hex(self._active_configserver.get_config_iocs_json()))
                    self.setParam("SERVER_STATUS", compress_and_hex(self.get_server_status()))
                    # Update them
                    self.updatePVs()
            sleep(2)

    def update_config_iocs_monitors(self):
        with self.monitor_lock:
            self.setParam("CONFIG_IOCS", compress_and_hex(self._active_configserver.get_config_iocs_json()))
            self.updatePVs()

    def update_get_details_monitors(self):
        self._config_list.set_active_changed(False)
        with self.monitor_lock:
            self.setParam("GET_CURR_CONFIG_DETAILS", compress_and_hex(self._active_configserver.get_config_details()))
            self.updatePVs()

    def consume_write_queue(self):
        # Queue items are tuples with three values
        # (the method to call, the argument(s) to send (tuple), the description of the state (string))
        # For example:
        # (self.load_config, ("configname",), "LOADING_CONFIG")
        while True:
            while len(self.write_queue) > 0:
                with self.write_lock:
                    cmd, arg, state = self.write_queue.pop(0)
                    self._status = state
                    cmd(*arg)
                    self._status = ""
            sleep(1)

    def get_server_status(self):
        d = dict()
        d['status'] = self._status
        return json.dumps(d).encode('ascii', 'replace')

    def get_blank_config(self):
        temp_config = ConfigServerManager(CONFIG_DIR, MACROS)
        return temp_config.get_config_details()

    def _check_config_inactive(self, inactive_name, is_subconfig=False):
        if not is_subconfig:
            if inactive_name == self._active_configserver.get_config_name():
                raise ValueError("Cannot change config, use SET_CURR_CONFIG_DETAILS to change the active config")
        else:
            pass
            # TODO: check not a component of active, don't know what do to for this case?


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-cd', '--config_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration (default=current directory)')
    parser.add_argument('-sd', '--schema_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration schema (default=current directory)')
    parser.add_argument('-od', '--options_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration options(default=current directory)')
    parser.add_argument('-g', '--gateway_prefix', nargs=1, type=str, default=['%MYPVPREFIX%CS:GATEWAY:BLOCKSERVER:'],
                        help='The prefix for the blocks gateway (default=%MYPVPREFIX%CS:GATEWAY:BLOCKSERVER:)')
    parser.add_argument('-b', '--block_prefix', nargs=1, type=str, default=['CS:SB:'],
                        help='The prefix for the blockserver (default=CS:SB:)')
    parser.add_argument('-pv', '--pvlist_name', nargs=1, type=str, default=['gwblock.pvlist'],
                        help='The filename for the pvlist file used by the blocks gateway (default=gwblock.pvlist)')
    parser.add_argument('-au', '--archive_uploader', nargs=1,
                        default=["%EPICS_KIT_ROOT%\\CSS\ArchiveEngine\\set_block_config.bat"],
                        help='The batch file used to upload settings to the PV Archiver')
    parser.add_argument('-as', '--archive_settings', nargs=1,
                        default=["%EPICS_KIT_ROOT%\\CSS\ArchiveEngine\\block_config.xml"],
                        help='The XML file containing the new PV Archiver log settings')

    args = parser.parse_args()

    BLOCK_PREFIX = args.block_prefix[0]
    if not BLOCK_PREFIX.endswith(':'):
        BLOCK_PREFIX += ":"
    print_and_log("BLOCK PREFIX = %s" % BLOCK_PREFIX)

    GATEWAY_PREFIX = args.gateway_prefix[0]
    if not GATEWAY_PREFIX.endswith(':'):
        GATEWAY_PREFIX += ":"
    GATEWAY_PREFIX = GATEWAY_PREFIX.replace('%MYPVPREFIX%', MACROS["$(MYPVPREFIX)"])
    print_and_log("BLOCK GATEWAY PREFIX = %s" % GATEWAY_PREFIX)

    CONFIG_DIR = os.path.abspath(args.config_dir[0])
    print_and_log("CONFIGURATION DIRECTORY = %s" % CONFIG_DIR)
    if not os.path.isdir(os.path.abspath(CONFIG_DIR)):
        # Create it then
        os.makedirs(os.path.abspath(CONFIG_DIR))

    SCHEMA_DIR = os.path.abspath(args.schema_dir[0])
    print_and_log("SCHEMA DIRECTORY = %s" % SCHEMA_DIR)

    ARCHIVE_UPLOADER = args.archive_uploader[0].replace('%EPICS_KIT_ROOT%', MACROS["$(EPICS_KIT_ROOT)"])
    print_and_log("ARCHIVE UPLOADER = %s" % ARCHIVE_UPLOADER)

    ARCHIVE_SETTINGS = args.archive_settings[0].replace('%EPICS_KIT_ROOT%', MACROS["$(EPICS_KIT_ROOT)"])
    print_and_log("ARCHIVE SETTINGS = %s" % ARCHIVE_SETTINGS)

    PVLIST_FILE = args.pvlist_name[0]

    print_and_log("BLOCKSERVER PREFIX = %s" % BLOCKSERVER_PREFIX)
    SERVER = CAServer(BLOCKSERVER_PREFIX)
    SERVER.createPV(BLOCKSERVER_PREFIX, PVDB)
    DRIVER = BlockServer(SERVER)

    # Process CA transactions
    while True:
        SERVER.process(0.1)
