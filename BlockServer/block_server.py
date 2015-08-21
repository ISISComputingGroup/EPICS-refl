# Add root path for access to server_commons and path for version control module
import os
import sys
sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))
sys.path.insert(0, os.path.abspath(os.environ["MYDIRVC"]))


# Standard imports
from pcaspy import Driver
import argparse
from threading import Thread, RLock
from time import sleep
import datetime
from BlockServer.epics.gateway import Gateway
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from server_common.channel_access_server import CAServer
from server_common.utilities import compress_and_hex, dehex_and_decompress, print_and_log, convert_to_json, convert_from_json
from BlockServer.core.macros import MACROS, BLOCKSERVER_PREFIX, BLOCK_PREFIX
from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.fileIO.file_watcher_manager import ConfigFileWatcherManager
from BlockServer.core.synoptic_manager import SynopticManager
from BlockServer.core.constants import SYNOPTIC_DIRECTORY
from BlockServer.config.json_converter import ConfigurationJsonConverter
from config_version_control import ConfigVersionControl
from vc_exceptions import NotUnderVersionControl
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.core.ioc_control import IocControl
from BlockServer.core.database_server_client import DatabaseServerClient
from BlockServer.core.runcontrol import RunControlManager
from BlockServer.epics.archiver_manager import ArchiverManager


# For documentation on these commands see the accompanying block_server.rst file
PVDB = {
    'BLOCKNAMES': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'BLOCK_DETAILS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'GROUPS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'COMPS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'LOAD_CONFIG': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'SAVE_CONFIG': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'LOAD_COMP': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'CLEAR_CONFIG': {
        'type': 'char',
        'count': 100,
        'value': [0],
    },
    'START_IOCS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'STOP_IOCS': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'RESTART_IOCS': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'CONFIGS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'GET_RC_OUT': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'GET_RC_PARS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'SET_RC_PARS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'GET_CURR_CONFIG_DETAILS': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'SET_CURR_CONFIG_DETAILS': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'SAVE_NEW_CONFIG': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'SAVE_NEW_COMPONENT': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'SERVER_STATUS': {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    'DELETE_CONFIGS': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'DELETE_COMPONENTS': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'BLANK_CONFIG': {
        'type': 'char',
        'count': 64000,
        'value': [0],
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
        'value': [0],
    },
    'SYNOPTICS:GET_DEFAULT': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'SYNOPTICS:SET_DETAILS': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'SYNOPTICS:DELETE': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'SYNOPTICS:SCHEMA': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'BUMPSTRIP_AVAILABLE': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },

    'BUMPSTRIP_AVAILABLE:SP': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },

}


class BlockServer(Driver):
    """The class for handling all the static PV access and monitors etc.
    """

    def __init__(self, ca_server):
        """Constructor.

        Args:
            ca_server (CAServer) : The CA server used for generating PVs on the fly
        """
        super(BlockServer, self).__init__()
        self._gateway = Gateway(GATEWAY_PREFIX, BLOCK_PREFIX, PVLIST_FILE)
        self._active_configserver = None
        self._status = "INITIALISING"
        self._ioc_control = IocControl(MACROS["$(MYPVPREFIX)"])
        self._db_client = DatabaseServerClient(BLOCKSERVER_PREFIX)
        self.bumpstrip = "No"

        # Connect to version control
        try:
            self._vc = ConfigVersionControl(CONFIG_DIR)
        except NotUnderVersionControl as err:
            print_and_log("Warning: Configurations not under version control", "INFO")
            self._vc = MockVersionControl()

        # Import data about all configs
        try:
            self._config_list = ConfigListManager(self, CONFIG_DIR, ca_server, SCHEMA_DIR, self._vc)
        except Exception as err:
            print_and_log("Error creating inactive config list: " + str(err), "MAJOR")

        # Import all the synoptic data and create PVs
        self._syn = SynopticManager(self, CONFIG_DIR + "\\" + SYNOPTIC_DIRECTORY, ca_server, SCHEMA_DIR, self._vc)

        # Start file watcher
        self._filewatcher = ConfigFileWatcherManager(CONFIG_DIR, SCHEMA_DIR, self._config_list, self._syn)

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

        with self.write_lock:
            self.write_queue.append((self.initialise_configserver, (), "INITIALISING"))

    def initialise_configserver(self):
        """Initialises the ActiveConfigHolder.
        """
        # This is in a separate method so it can be sent to the thread queue
        arch = ArchiverManager(ARCHIVE_UPLOADER, ARCHIVE_SETTINGS)
        rcm = RunControlManager(MACROS["$(MYPVPREFIX)"], MACROS["$(ICPCONFIGROOT)"], MACROS["$(ICPVARDIR)"],
                                self._ioc_control)
        self._active_configserver = ActiveConfigHolder(CONFIG_DIR, MACROS, arch, self._vc, self._ioc_control, rcm)

        try:
            if self._gateway.exists():
                print_and_log("Found gateway")
                self.load_last_config()
            else:
                print_and_log("Could not connect to gateway - is it running?")
                self.load_last_config()
        except Exception as err:
            print_and_log("Could not load last configuration. Message was: %s" % err, "MAJOR")
            self._active_configserver.clear_config()

        # Update monitors to current values
        self.update_blocks_monitors()
        self.update_config_monitors()

    def read(self, reason):
        """A method called by SimpleServer when a PV is read from the BlockServer over Channel Access.

        Args:
            reason (string) : The PV that is being requested (without the PV prefix)

        Returns:
            string : A compressed and hexed JSON formatted string that gives the desired information based on reason. If an
                Exception is thrown in the reading of the information this is returned in compressed and hexed JSON.
        """
        try:
            if reason == 'BLOCKNAMES':
                bn = convert_to_json(self._active_configserver.get_blocknames())
                value = compress_and_hex(bn)
            elif reason == 'GROUPS':
                grps = ConfigurationJsonConverter.groups_to_json(self._active_configserver.get_group_details())
                value = compress_and_hex(grps)
            elif reason == 'CONFIGS':
                value = compress_and_hex(convert_to_json(self._config_list.get_configs()))
            elif reason == 'COMPS':
                value = compress_and_hex(convert_to_json(self._config_list.get_subconfigs()))
            elif reason == 'GET_RC_OUT':
                js = convert_to_json(self._active_configserver.get_out_of_range_pvs())
                value = compress_and_hex(js)
            elif reason == 'GET_RC_PARS':
                pars = convert_to_json(self._active_configserver.get_runcontrol_settings())
                value = compress_and_hex(pars)
            elif reason == "GET_CURR_CONFIG_DETAILS":
                value = compress_and_hex(convert_to_json(self._active_configserver.get_config_details()))
            elif reason == "SERVER_STATUS":
                value = compress_and_hex(self.get_server_status())
            elif reason == "BLANK_CONFIG":
                js = convert_to_json(self.get_blank_config())
                value = compress_and_hex(js)
            elif reason == "SYNOPTICS:NAMES":
                value = compress_and_hex(convert_to_json(self._syn.get_synoptic_list()))
            elif reason == "SYNOPTICS:GET_DEFAULT":
                value = compress_and_hex(self._syn.get_default_synoptic_xml())
            elif reason == "SYNOPTICS:SCHEMA":
                value = compress_and_hex(self._syn.get_synoptic_schema())
            elif reason == "BUMPSTRIP_AVAILABLE":
                value = compress_and_hex(self.bumpstrip)
            else:
                value = self.getParam(reason)
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        return value

    def write(self, reason, value):
        """A method called by SimpleServer when a PV is written to the BlockServer over Channel Access. The write
            commands are queued as Channel Access is single-threaded.

        Args:
            reason (string) : The PV that is being requested (without the PV prefix)
            value (string) : The data being written to the 'reason' PV

        Returns:
            string : "OK" in compressed and hexed JSON if function succeeds. Otherwise returns the Exception in compressed
                and hexed JSON.
        """
        status = True
        try:
            self._filewatcher.pause()
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
                self._ioc_control.start_iocs(convert_from_json(data))
            elif reason == 'STOP_IOCS':
                self._ioc_control.stop_iocs(convert_from_json(data))
            elif reason == 'RESTART_IOCS':
                self._ioc_control.restart_iocs(convert_from_json(data))
            elif reason == 'SET_RC_PARS':
                self._active_configserver.set_runcontrol_settings(convert_from_json(data))
            elif reason == 'SET_CURR_CONFIG_DETAILS':
                self._active_configserver.set_config_details(convert_from_json(data))
                self._initialise_config()
            elif reason == 'SAVE_NEW_CONFIG':
                self.save_inactive_config(data)
            elif reason == 'SAVE_NEW_COMPONENT':
                self.save_inactive_config(data, True)
            elif reason == 'DELETE_CONFIGS':
                self._config_list.delete_configs(convert_from_json(data))
                self.update_config_monitors()
            elif reason == 'DELETE_COMPONENTS':
                self._config_list.delete_configs(convert_from_json(data), True)
                self.update_comp_monitor()
            elif reason == 'ACK_CURR_CHANGED':
                self._config_list.set_active_changed(False)
            elif reason == "SYNOPTICS:SET_DETAILS":
                self._syn.save_synoptic_xml(data)
                self.update_synoptic_monitor()
            elif reason == "SYNOPTICS:DELETE":
                self._syn.delete_synoptics(convert_from_json(data))
                self.update_synoptic_monitor()
            elif reason == "BUMPSTRIP_AVAILABLE:SP":
                self.bumpstrip = data
                self.update_bumpstripAvailability()
            else:
                status = False
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        else:
            if status:
                value = compress_and_hex(convert_to_json("OK"))
        finally:
            self._filewatcher.resume()

        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def load_last_config(self):
        """Loads the last configuration used.

        The information is saved in a text file.
        """
        last = self._active_configserver.load_last_config()
        if last is None:
            print_and_log("Could not retrieve last configuration - starting blank configuration")
            self._active_configserver.clear_config()
        else:
            print_and_log("Loaded last configuration: %s" % last)
        self._initialise_config()

    def _initialise_config(self, init_gateway=True, clear_runcontrol=False):
        """Responsible for initialising the configuration.
        Sets all the monitors, initialises the gateway, sets up run-control etc.

        Args:
            init_gateway (bool, optional) : whether to initialise the gateway
            clear_runcontrol (bool, optional) : whether to delete the autosave settings for run-control
        """
        # First stop all IOCS, then start the ones for the config
        # TODO: Should we stop all configs?
        iocs_to_start, iocs_to_restart = self._active_configserver.iocs_changed()

        # If the config has a default synoptic then set the PV to that
        synoptic = self._active_configserver.get_config_meta().synoptic
        self._syn.set_default_synoptic(synoptic)
        self.update_synoptic_monitor()

        if len(iocs_to_start) > 0 or len(iocs_to_restart) > 0:
            self._stop_iocs_and_start_config_iocs(iocs_to_start, iocs_to_restart)
        # Set up the gateway
        if init_gateway:
            self._gateway.set_new_aliases(self._active_configserver.get_block_details())
        self._config_list.active_config_name = self._active_configserver.get_config_name()
        self._config_list.active_components = self._active_configserver.get_component_names()
        self.update_blocks_monitors()
        self.update_config_monitors()
        self.update_get_details_monitors()
        self._active_configserver.update_archiver()
        self._active_configserver.create_runcontrol_pvs(clear_runcontrol)

    def _stop_iocs_and_start_config_iocs(self, iocs_to_start, iocs_to_restart):
        """ Stop all IOCs and start the IOCs that are part of the configuration."""
        non_conf_iocs = [x for x in self._get_iocs() if x not in self._active_configserver.get_ioc_names()]
        self._ioc_control.stop_iocs(non_conf_iocs)
        self._start_config_iocs()

    def _start_config_iocs(self):
        # Start the IOCs, if they are available and if they are flagged for autostart
        for n, ioc in self._active_configserver.get_ioc_details().iteritems():
            try:
                # Throws if IOC does not exist
                # If it is already running restart it, otherwise start it
                running = self._ioc_control.get_ioc_status(n)
                if running == "RUNNING" and ioc.restart:
                    self._ioc_control.restart_ioc(n)
                else:
                    if ioc.autostart:
                        self._ioc_control.start_ioc(n)
            except Exception as err:
                print_and_log("Could not (re)start IOC %s: %s" % (n, str(err)), "MAJOR")

    def _get_iocs(self, include_running=False):
        # Get IOCs from DatabaseServer
        try:
            return self._db_client.get_iocs()
        except Exception as err:
            print_and_log("Could not retrieve IOC list: %s" % str(err), "MAJOR")
            return []

    def load_config(self, config, is_subconfig=False):
        """Load a configuration.

        Args:
            config (string) : The name of the configuration
            is_subconfig (bool) : Whether it is a component or not
        """
        try:
            if is_subconfig:
                print_and_log("Loading sub-configuration: %s" % config)
                self._active_configserver.load_active(config, True)
            else:
                print_and_log("Loading configuration: %s" % config)
                self._active_configserver.load_active(config)
            # If we get this far then assume the config is okay
            self._initialise_config(clear_runcontrol=True)
        except Exception as err:
            print_and_log(str(err), "MAJOR")

    def save_inactive_config(self, json_data, as_subconfig=False):
        """Save an inactive configuration.

        Args:
            json_data (string) : The JSON data containing the configuration/component
            as_subconfig (bool) : Whether it is a component or not
        """
        new_details = convert_from_json(json_data)
        inactive = InactiveConfigHolder(CONFIG_DIR, MACROS, self._vc)

        history = self._get_inactive_history(new_details["name"], as_subconfig)

        inactive.set_config_details(new_details)

        # Set updated history
        history.append(self._get_timestamp())
        inactive.set_history(history)

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
            print_and_log("Saved")
        finally:
            self._filewatcher.resume()

    def _get_inactive_history(self, name, is_component=False):
        # If it already exists load it
        try:
            inactive = InactiveConfigHolder(CONFIG_DIR, MACROS, self._vc)
            inactive.load_inactive(name, is_component)
            # Get previous history
            history = inactive.get_history()
        except IOError as err:
            # Config doesn't exist therefore start new history
            history = list()
        return history

    def _get_timestamp(self):
        return datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')

    def save_active_config(self, name):
        """Save the active configuration.

        Args:
            name (string) : The name to save it under
        """
        self._filewatcher.pause()
        try:
            print_and_log("Saving active configuration as: %s" % name)
            oldname = self._active_configserver.get_cached_name()
            if oldname != "" and name != oldname:
                # New name or overwriting another config (Save As)
                history = self._get_inactive_history(name)
            else:
                # Saving current config (Save)
                history = self._active_configserver.get_history()

            # Set updated history
            history.append(self._get_timestamp())
            self._active_configserver.set_history(history)

            self._active_configserver.save_active(name)
            self._config_list.update_a_config_in_list(self._active_configserver)
            self.update_config_monitors()
        finally:
            self._filewatcher.resume()

    def update_blocks_monitors(self):
        """Updates the monitors for the blocks and groups, so the clients can see any changes.
        """
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
        """Updates the monitor for the configurations, so the clients can see any changes.
        """
        with self.monitor_lock:
            # set the available configs
            self.setParam("CONFIGS", compress_and_hex(convert_to_json(self._config_list.get_configs())))
            # Update them
            self.updatePVs()

    def update_comp_monitor(self):
        """Updates the monitor for the components, so the clients can see any changes.
        """
        with self.monitor_lock:
            self.setParam("COMPS", compress_and_hex(convert_to_json(self._config_list.get_subconfigs())))
            # Update them
            self.updatePVs()

    def update_ioc_monitors(self):
        """Updates the monitor for the server status, so the clients can see any changes.
        """
        # TODO: Rename this method!
        while True:
            if self._active_configserver is not None:
                with self.monitor_lock:
                    self.setParam("SERVER_STATUS", compress_and_hex(self.get_server_status()))
                    # Update them
                    self.updatePVs()
            sleep(2)

    def update_get_details_monitors(self):
        """Updates the monitor for the active configuration, so the clients can see any changes.
        """
        self._config_list.set_active_changed(False)
        with self.monitor_lock:
            js = convert_to_json(self._active_configserver.get_config_details())
            self.setParam("GET_CURR_CONFIG_DETAILS", compress_and_hex(js))
            self.updatePVs()

    def update_synoptic_monitor(self):
        """Updates the monitor for the current synoptic, so the clients can see any changes.
        """
        with self.monitor_lock:
            synoptic = self._syn.get_default_synoptic_xml()
            self.setParam("SYNOPTICS:GET_DEFAULT", compress_and_hex(synoptic))
            names = convert_to_json(self._syn.get_synoptic_list())
            self.setParam("SYNOPTICS:NAMES", compress_and_hex(names))

    def update_bumpstripAvailability(self):
            """Updates the monitor for the configurations, so the clients can see any changes.
            """
            with self.monitor_lock:
                # set the available configs
                self.setParam("BUMPSTRIP_AVAILABLE", compress_and_hex(self.bumpstrip))
                # Update them
                self.updatePVs()

    def consume_write_queue(self):
        """Actions any requests on the write queue.

        Queue items are tuples with three values:
        the method to call; the argument(s) to send (tuple); and, the description of the state (string))

        For example:
            self.load_config, ("configname",), "LOADING_CONFIG")
        """
        while True:
            while len(self.write_queue) > 0:
                with self.write_lock:
                    cmd, arg, state = self.write_queue.pop(0)
                    self._status = state
                    cmd(*arg)
                    self._status = ""
            sleep(1)

    def get_server_status(self):
        """Get the status of the BlockServer.

        Returns:
            string : A JSON representation of the status
        """
        d = dict()
        d['status'] = self._status
        return convert_to_json(d)

    def get_blank_config(self):
        """Get a blank configuration which can be used to create a new configuration from scratch.

        Returns:
            dict : A dictionary containing all the details of a blank configuration
        """
        temp_config = InactiveConfigHolder(CONFIG_DIR, MACROS, self._vc)
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
                        default=["%EPICS_KIT_ROOT%\\CSS\\master\\ArchiveEngine\\set_block_config.bat"],
                        help='The batch file used to upload settings to the PV Archiver')
    parser.add_argument('-as', '--archive_settings', nargs=1,
                        default=["%EPICS_KIT_ROOT%\\CSS\\master\\ArchiveEngine\\block_config.xml"],
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
