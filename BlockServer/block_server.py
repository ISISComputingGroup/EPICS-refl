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
from BlockServer.epics.gateway import Gateway
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from server_common.channel_access_server import CAServer
from server_common.utilities import compress_and_hex, dehex_and_decompress, print_and_log, convert_to_json
from BlockServer.core.macros import MACROS, BLOCKSERVER_PREFIX, BLOCK_PREFIX
from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.fileIO.file_watcher_manager import ConfigFileWatcherManager
from BlockServer.core.synoptic_manager import SynopticManager
from BlockServer.core.constants import SYNOPTIC_DIRECTORY
from BlockServer.config.json_converter import ConfigurationJsonConverter

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
    'CLEAR_CONFIG': {
        'type': 'char',
        'count': 100,
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
    },
    'SYNOPTICS:NAMES': {
        'type': 'char',
        'count': 16000,
    },
    'SYNOPTICS:GET_CURRENT': {
        'type': 'char',
        'count': 16000,
    },
}


class BlockServer(Driver):
    def __init__(self, ca_server):
        super(BlockServer, self).__init__()
        self._gateway = Gateway(GATEWAY_PREFIX, BLOCK_PREFIX, PVLIST_FILE)
        self._active_configserver = None
        self._status = "INITIALISING"

        # Import data about all configs
        try:
            self._config_list = ConfigListManager(self, CONFIG_DIR, ca_server, SCHEMA_DIR)
        except Exception as err:
            print_and_log("Error creating inactive config list: " + str(err), "ERROR")

        # Import all the synoptic data and create PVs
        try:
            self._syn = SynopticManager(CONFIG_DIR + "\\" + SYNOPTIC_DIRECTORY, ca_server)
            self._syn.create_pvs()
        except Exception as err:
            print_and_log("Error creating synoptic PVs: %s" % str(err), "ERROR")

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
        # This is in a separate method so it can be sent to the thread queue
        self._active_configserver = ActiveConfigHolder(CONFIG_DIR, MACROS, ARCHIVE_UPLOADER, ARCHIVE_SETTINGS)
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
                bn = json.dumps(self._active_configserver.get_blocknames())
                value = compress_and_hex(bn)
            elif reason == 'GROUPS':
                grps = ConfigurationJsonConverter.groups_to_json(self._active_configserver.get_group_details())
                value = compress_and_hex(grps)
            elif reason == 'CONFIGS':
                value = compress_and_hex(self._config_list.get_configs_json())
            elif reason == 'COMPS':
                value = compress_and_hex(self._config_list.get_subconfigs_json())
            elif reason == 'GET_RC_OUT':
                js = convert_to_json(self._active_configserver.get_out_of_range_pvs())
                value = compress_and_hex(js)
            elif reason == 'GET_RC_PARS':
                pars = convert_to_json(self._active_configserver.get_runcontrol_settings())
                value = compress_and_hex(pars)
            elif reason == "GET_CURR_CONFIG_DETAILS":
                value = compress_and_hex(json.dumps(self._active_configserver.get_config_details()))
            elif reason == "SERVER_STATUS":
                value = compress_and_hex(self.get_server_status())
            elif reason == "BLANK_CONFIG":
                js = convert_to_json(self.get_blank_config())
                value = compress_and_hex(js)
            elif reason == "SYNOPTICS:NAMES":
                value = compress_and_hex(convert_to_json(self._syn.get_synoptic_filenames()))
            elif reason == "SYNOPTICS:GET_CURRENT":
                value = compress_and_hex(self._syn.get_current_synoptic_xml())
            else:
                value = self.getParam(reason)
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "ERROR")
        return value

    def write(self, reason, value):
        # This is called by CA
        # All write commands are queued as CA is single-threaded
        status = True
        try:
            data = dehex_and_decompress(value).strip('"')
            if reason == 'LOAD_CONFIG':
                with self.write_lock:
                    self.write_queue.append((self.load_config, (data,), "LOADING_CONFIG"))
            elif reason == 'SAVE_CONFIG':
                self.save_active_config(data)
            elif reason == 'LOAD_COMP':
                with self.write_lock:
                    self.write_queue.append((self.load_config, (data, True), "LOADING_COMP"))
                self.update_blocks_monitors()
            elif reason == 'CLEAR_CONFIG':
                self._active_configserver.clear_config()
                self._initialise_config()
            elif reason == 'START_IOCS':
                self._active_configserver.start_iocs(json.loads(data))
            elif reason == 'STOP_IOCS':
                self._active_configserver.stop_iocs(json.loads(data))
            elif reason == 'RESTART_IOCS':
                self._active_configserver.restart_iocs(json.loads(data))
            elif reason == 'SET_RC_PARS':
                self._active_configserver.set_runcontrol_settings(json.loads(data))
            elif reason == 'SET_CURR_CONFIG_DETAILS':
                self._active_configserver.set_config_details(json.loads(data))
                self._initialise_config()
            elif reason == 'SAVE_NEW_CONFIG':
                self.save_inactive_config(data)
            elif reason == 'SAVE_NEW_COMPONENT':
                self.save_inactive_config(data, True)
            elif reason == 'DELETE_CONFIGS':
                self._config_list.delete_configs_json(data)
                self.update_config_monitors()
            elif reason == 'DELETE_COMPONENTS':
                self._config_list.delete_configs_json(data, True)
                self.update_comp_monitor()
            elif reason == 'ACK_CURR_CHANGED':
                self._config_list.set_active_changed(False)
            else:
                status = False
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "ERROR")
        else:
            if status:
                value = compress_and_hex(convert_to_json("OK"))

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
            self._gateway.set_new_aliases(self._active_configserver.get_block_details())
        self._config_list.active_config_name = self._active_configserver.get_config_name()
        self._config_list.active_components = self._active_configserver.get_component_names()
        self.update_blocks_monitors()
        self.update_config_monitors()
        self.update_get_details_monitors()
        self._active_configserver.update_archiver()
        # TODO: self._active_configserver.create_runcontrol_pvs()

    def load_config(self, config, is_subconfig=False):
        try:
            if is_subconfig:
                print_and_log("Loading sub-configuration: %s" % config)
                self._active_configserver.load_active(config, True)
            else:
                print_and_log("Loading configuration: %s" % config)
                self._active_configserver.load_active(config)
            # If we get this far then assume the config is okay
            self._initialise_config()
        except Exception as err:
            print_and_log(str(err), "ERROR")

    def save_inactive_config(self, json_data, as_subconfig=False):
        inactive = InactiveConfigHolder(CONFIG_DIR, MACROS)
        inactive.set_config_details(json.loads(json_data))
        config_name = inactive.get_config_name()
        self._check_config_inactive(config_name, as_subconfig)
        self._filewatcher.pause()
        try:
            if not as_subconfig:
                print_and_log("Saving configuration: %s" % config_name)
                inactive.save_inactive()
                self._config_list.update_a_config_in_list(inactive)
                self.update_config_monitors()
            else:
                print_and_log("Saving sub-configuration: %s" % config_name)
                inactive.save_inactive(as_comp=True)
                self._config_list.update_a_config_in_list(inactive, True)
                self.update_comp_monitor()
        finally:
            self._filewatcher.resume()

    def save_active_config(self, name):
        self._filewatcher.pause()
        try:
            print_and_log("Saving active configuration as: %s" % name)
            self._active_configserver.save_active(name)
            self._config_list.update_a_config_in_list(self._active_configserver)
            self.update_config_monitors()
        finally:
            self._filewatcher.resume()

    def update_blocks_monitors(self):
        with self.monitor_lock:
            # Blocks
            bn = convert_to_json(self._active_configserver.get_blocknames())
            self.setParam("BLOCKNAMES", compress_and_hex(bn))
            # Groups
            # Update the PV, so that groupings are updated for any CA monitors
            grps = ConfigurationJsonConverter.groups_to_json(self._active_configserver.get_group_details())
            self.setParam("GROUPS", compress_and_hex(grps))
            # Update them
            self.updatePVs()

    def update_config_monitors(self):
        with self.monitor_lock:
            # set the available configs
            self.setParam("CONFIGS", compress_and_hex(self._config_list.get_configs_json()))
            # Update them
            self.updatePVs()

    def update_comp_monitor(self):
        with self.monitor_lock:
            self.setParam("COMPS", compress_and_hex(self._config_list.get_subconfigs_json()))
            # Update them
            self.updatePVs()

    def update_ioc_monitors(self):
        while True:
            if self._active_configserver is not None:
                with self.monitor_lock:
                    self.setParam("SERVER_STATUS", compress_and_hex(self.get_server_status()))
                    # Update them
                    self.updatePVs()
            sleep(2)

    def update_get_details_monitors(self):
        self._config_list.set_active_changed(False)
        with self.monitor_lock:
            js = convert_to_json(self._active_configserver.get_config_details())
            self.setParam("GET_CURR_CONFIG_DETAILS", compress_and_hex(js))
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
        return convert_to_json(d)

    def get_blank_config(self):
        temp_config = InactiveConfigHolder(CONFIG_DIR, MACROS)
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
    parser.add_argument('-pv', '--pvlist_name', nargs=1, type=str, default=['gwblock.pvlist'],
                        help='The filename for the pvlist file used by the blocks gateway (default=gwblock.pvlist)')
    parser.add_argument('-au', '--archive_uploader', nargs=1,
                        default=["%EPICS_KIT_ROOT%\\CSS\\ArchiveEngine\\set_block_config.bat"],
                        help='The batch file used to upload settings to the PV Archiver')
    parser.add_argument('-as', '--archive_settings', nargs=1,
                        default=["%EPICS_KIT_ROOT%\\CSS\\ArchiveEngine\\block_config.xml"],
                        help='The XML file containing the new PV Archiver log settings')

    args = parser.parse_args()

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
