# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

# Add root path for access to server_commons and path for version control module
import os
import sys

sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))

# Standard imports
from pcaspy import Driver, SimpleServer
import argparse
from threading import Thread, RLock
from time import sleep
import datetime
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.epics.gateway import Gateway
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from server_common.channel_access_server import CAServer
from server_common.utilities import compress_and_hex, dehex_and_decompress, print_and_log, set_logger, \
    convert_to_json, convert_from_json
from BlockServer.core.macros import MACROS, BLOCKSERVER_PREFIX, BLOCK_PREFIX
from BlockServer.core.pv_names import BlockserverPVNames
from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.fileIO.config_file_watcher_manager import ConfigFileWatcherManager
from BlockServer.synoptic.synoptic_manager import SynopticManager
from BlockServer.devices.devices_manager import DevicesManager
from BlockServer.config.json_converter import ConfigurationJsonConverter
from ConfigVersionControl.git_version_control import GitVersionControl, RepoFactory
from ConfigVersionControl.vc_exceptions import NotUnderVersionControl
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.core.ioc_control import IocControl
from BlockServer.core.database_server_client import DatabaseServerClient
from BlockServer.runcontrol.runcontrol_manager import RunControlManager
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.block_cache_manager import BlockCacheManager
from BlockServer.site_specific.default.block_rules import BlockRules
from pcaspy.driver import manager, Data
from BlockServer.site_specific.default.general_rules import GroupRules, ConfigurationDescriptionRules
from BlockServer.spangle_banner.banner import Banner
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from WebServer.simple_webserver import Server

# For documentation on these commands see the wiki
PVDB = {
    BlockserverPVNames.BLOCKNAMES: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.BLOCK_DETAILS: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.GROUPS: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.COMPS: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.LOAD_CONFIG: {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    BlockserverPVNames.SAVE_CONFIG: {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    BlockserverPVNames.RELOAD_CURRENT_CONFIG: {
        'type': 'char',
        'count': 100,
        'value': [0],
    },
    BlockserverPVNames.START_IOCS: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.STOP_IOCS: {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    BlockserverPVNames.RESTART_IOCS: {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    BlockserverPVNames.CONFIGS: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.GET_CURR_CONFIG_DETAILS: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.SET_CURR_CONFIG_DETAILS: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.SAVE_NEW_CONFIG: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.SAVE_NEW_COMPONENT: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.SERVER_STATUS: {
        'type': 'char',
        'count': 1000,
        'value': [0],
    },
    BlockserverPVNames.DELETE_CONFIGS: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.DELETE_COMPONENTS: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.BLANK_CONFIG: {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    BlockserverPVNames.BUMPSTRIP_AVAILABLE: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.BUMPSTRIP_AVAILABLE_SP: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    BlockserverPVNames.BANNER_DESCRIPTION: {
        'type': 'char',
        'count': 16000,
        'value': [0],
    }
}


class BlockServer(Driver):
    """The class for handling all the static PV access and monitors etc.
    """

    def __init__(self, ca_server):
        """Constructor.

        Args:
            ca_server (CAServer): The CA server used for generating PVs on the fly
        """
        super(BlockServer, self).__init__()

        # Threading stuff
        self.monitor_lock = RLock()
        self.write_lock = RLock()
        self.write_queue = list()

        FILEPATH_MANAGER.initialise(CONFIG_DIR, SCHEMA_DIR)

        self._cas = ca_server
        self._gateway = Gateway(GATEWAY_PREFIX, BLOCK_PREFIX, PVLIST_FILE, MACROS["$(MYPVPREFIX)"])
        self._active_configserver = None
        self._run_control = None
        self._block_cache = None
        self._syn = None
        self._devices = None
        self._filewatcher = None
        self.on_the_fly_handlers = list()
        self._ioc_control = IocControl(MACROS["$(MYPVPREFIX)"])
        self._db_client = DatabaseServerClient(BLOCKSERVER_PREFIX + "BLOCKSERVER:")
        self.bumpstrip = "No"
        self.block_rules = BlockRules(self)
        self.group_rules = GroupRules(self)
        self.config_desc = ConfigurationDescriptionRules(self)

        # Connect to version control
        try:
            self._vc = GitVersionControl(CONFIG_DIR, RepoFactory.get_repo(CONFIG_DIR))
            self._vc.setup()
        except NotUnderVersionControl as err:
            print_and_log("Warning: Configurations not under version control", "MINOR")
            self._vc = MockVersionControl()
        except Exception as err:
            print_and_log("Unable to start version control. Modifications to the instrument setup will not be "
                          "tracked: " + str(err), "MINOR")
            self._vc = MockVersionControl()

        # Create banner object
        self.banner = Banner(MACROS["$(MYPVPREFIX)"])

        # Import data about all configs
        try:
            self._config_list = ConfigListManager(self, SCHEMA_DIR, self._vc, ConfigurationFileManager())
        except Exception as err:
            print_and_log(
                "Error creating inactive config list. Configuration list changes will not be stored " +
                "in version control: %s " % str(err), "MINOR")
            self._config_list = ConfigListManager(self, SCHEMA_DIR, MockVersionControl(), ConfigurationFileManager())

        # Start a background thread for handling write commands
        write_thread = Thread(target=self.consume_write_queue, args=())
        write_thread.daemon = True  # Daemonise thread
        write_thread.start()

        with self.write_lock:
            self.write_queue.append((self.initialise_configserver, (FACILITY,), "INITIALISING"))

        # Starts the Web Server
        self.server = Server()
        self.server.start()

    def initialise_configserver(self, facility):
        """Initialises the ActiveConfigHolder.

        Args:
            facility (string): The facility using the BlockServer
        """
        # This is in a separate method so it can be sent to the thread queue
        arch = ArchiverManager(ARCHIVE_UPLOADER, ARCHIVE_SETTINGS)

        self._active_configserver = ActiveConfigHolder(MACROS, arch, self._vc, ConfigurationFileManager(),
                                                       self._ioc_control)

        if facility == "ISIS":
            self._run_control = RunControlManager(MACROS["$(MYPVPREFIX)"], MACROS["$(ICPCONFIGROOT)"],
                                                  MACROS["$(ICPVARDIR)"], self._ioc_control, self._active_configserver,
                                                  self)
            self.on_the_fly_handlers.append(self._run_control)
            self._block_cache = BlockCacheManager(self._ioc_control)

        # Import all the synoptic data and create PVs
        self._syn = SynopticManager(self, SCHEMA_DIR, self._vc, self._active_configserver)
        self.on_the_fly_handlers.append(self._syn)

        # Import all the devices data and create PVs
        self._devices = DevicesManager(self, SCHEMA_DIR, self._vc, self._active_configserver)
        self.on_the_fly_handlers.append(self._devices)

        # Start file watcher
        self._filewatcher = ConfigFileWatcherManager(SCHEMA_DIR, self._config_list, self._syn)

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
            self._initialise_config()

    def read(self, reason):
        """A method called by SimpleServer when a PV is read from the BlockServer over Channel Access.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)

        Returns:
            string : A compressed and hexed JSON formatted string that gives the desired information based on reason.
            If an Exception is thrown in the reading of the information this is returned in compressed and hexed JSON.
        """
        try:
            if reason == BlockserverPVNames.GROUPS:
                grps = ConfigurationJsonConverter.groups_to_json(self._active_configserver.get_group_details())
                value = compress_and_hex(grps)
            elif reason == BlockserverPVNames.CONFIGS:
                value = compress_and_hex(convert_to_json(self._config_list.get_configs()))
            elif reason == BlockserverPVNames.COMPS:
                value = compress_and_hex(convert_to_json(self._config_list.get_components()))
            elif reason == BlockserverPVNames.BLANK_CONFIG:
                js = convert_to_json(self.get_blank_config())
                value = compress_and_hex(js)
            elif reason == BlockserverPVNames.BUMPSTRIP_AVAILABLE:
                value = compress_and_hex(self.bumpstrip)
            elif reason == BlockserverPVNames.BANNER_DESCRIPTION:
                value = compress_and_hex(self.banner.get_description())
            else:
                # Check to see if it is a on-the-fly PV
                for handler in self.on_the_fly_handlers:
                    if handler.read_pv_exists(reason):
                        return handler.handle_pv_read(reason)

                value = self.getParam(reason)
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        return value

    def write(self, reason, value):
        """A method called by SimpleServer when a PV is written to the BlockServer over Channel Access. The write
            commands are queued as Channel Access is single-threaded.

            Note that the filewatcher is disabled as part of the write queue so any operations that intend to modify
            files should use the write queue.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)
            value (string): The data being written to the 'reason' PV

        Returns:
            string : "OK" in compressed and hexed JSON if function succeeds. Otherwise returns the Exception in
            compressed and hexed JSON.
        """
        status = True
        try:
            data = dehex_and_decompress(value).strip('"')
            if reason == BlockserverPVNames.LOAD_CONFIG:
                with self.write_lock:
                    self.write_queue.append((self.load_config, (data,), "LOADING_CONFIG"))
            elif reason == BlockserverPVNames.SAVE_CONFIG:
                with self.write_lock:
                    self.write_queue.append((self.save_active_config, (data,), "SAVING_CONFIG"))
            elif reason == BlockserverPVNames.RELOAD_CURRENT_CONFIG:
                with self.write_lock:
                    self.write_queue.append((self.reload_current_config, (), "RELOAD_CURRENT_CONFIG"))
            elif reason == BlockserverPVNames.START_IOCS:
                with self.write_lock:
                    self.write_queue.append((self.start_iocs, (convert_from_json(data),), "START_IOCS"))
            elif reason == BlockserverPVNames.STOP_IOCS:
                with self.write_lock:
                    self.write_queue.append((self._ioc_control.stop_iocs, (convert_from_json(data),), "STOP_IOCS"))
            elif reason == BlockserverPVNames.RESTART_IOCS:
                with self.write_lock:
                    self.write_queue.append((self._ioc_control.restart_iocs, (convert_from_json(data), True),
                                             "RESTART_IOCS"))
            elif reason == BlockserverPVNames.SET_CURR_CONFIG_DETAILS:
                with self.write_lock:
                    self.write_queue.append((self._set_curr_config, (convert_from_json(data),), "SETTING_CONFIG"))
            elif reason == BlockserverPVNames.SAVE_NEW_CONFIG:
                with self.write_lock:
                    self.write_queue.append((self.save_inactive_config, (data,), "SAVING_NEW_CONFIG"))
            elif reason == BlockserverPVNames.SAVE_NEW_COMPONENT:
                with self.write_lock:
                    self.write_queue.append((self.save_inactive_config, (data, True), "SAVING_NEW_COMP"))
            elif reason == BlockserverPVNames.DELETE_CONFIGS:
                with self.write_lock:
                    self.write_queue.append((self._config_list.delete_configs, (convert_from_json(data),),
                                             "DELETE_CONFIGS"))
            elif reason == BlockserverPVNames.DELETE_COMPONENTS:
                with self.write_lock:
                    self.write_queue.append((self._config_list.delete_configs, (convert_from_json(data), True),
                                             "DELETE_COMPONENTS"))
            elif reason == BlockserverPVNames.BUMPSTRIP_AVAILABLE_SP:
                self.bumpstrip = data
                with self.write_lock:
                    self.write_queue.append((self.update_bumpstrip_availability, None, "UPDATE_BUMPSTRIP"))
            else:
                status = False
                # Check to see if it is a on-the-fly PV
                for h in self.on_the_fly_handlers:
                    if h.write_pv_exists(reason):
                        with self.write_lock:
                            self.write_queue.append((h.handle_pv_write, (reason, data), "SETTING_CONFIG"))
                        status = True
                        break

        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        else:
            if status:
                value = compress_and_hex(convert_to_json("OK"))

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

    def _set_curr_config(self, details):
        """Sets the current configuration details to that defined in the XML, saves to disk, then initialises it.

        Args:
            details (string): the configuration XML
        """
        self._active_configserver.set_config_details(details)
        # Need to save the config to file before we initialize or the changes won't be propagated to IOCS
        self.save_active_config(self._active_configserver.get_config_name())
        self._initialise_config()

    def _initialise_config(self, init_gateway=True, full_init=False):
        """Responsible for initialising the configuration.
        Sets all the monitors, initialises the gateway, etc.

        Args:
            init_gateway (bool, optional): whether to initialise the gateway
            full_init (bool, optional): whether this requires a full initialisation, e.g. on loading a new
                configuration
        """
        # First stop all IOCS, then start the ones for the config
        # TODO: Should we stop all configs?
        iocs_to_start, iocs_to_restart = self._active_configserver.iocs_changed()

        if len(iocs_to_start) > 0 or len(iocs_to_restart) > 0:
            self._stop_iocs_and_start_config_iocs(iocs_to_start, iocs_to_restart)
        # Set up the gateway
        if init_gateway:
            self._gateway.set_new_aliases(self._active_configserver.get_block_details())

        self._config_list.active_config_name = self._active_configserver.get_config_name()
        self._config_list.active_components = self._active_configserver.get_component_names()
        self._config_list.update_monitors()

        self.update_blocks_monitors()

        self.update_get_details_monitors()
        self._active_configserver.update_archiver()

        for h in self.on_the_fly_handlers:
            h.initialise(full_init)

        # Update Web Server text
        self.server.set_config(convert_to_json(self._active_configserver.get_config_details()))

        # Restart the Blocks cache
        if self._block_cache is not None:
            print_and_log("Restarting block cache...")
            self._block_cache.restart()

    def _stop_iocs_and_start_config_iocs(self, iocs_to_start, iocs_to_restart):
        """ Stop all IOCs and start the IOCs that are part of the configuration."""
        # iocs_to_start, iocs_to_restart are not used at the moment, but longer term they could be used
        # for only restarting IOCs for which the setting have changed.
        non_conf_iocs = [x for x in self._get_iocs() if x not in self._active_configserver.get_ioc_names()]
        self._ioc_control.stop_iocs(non_conf_iocs)
        self._start_config_iocs()

    def _start_config_iocs(self):
        # Start the IOCs, if they are available and if they are flagged for autostart
        # Note: autostart means the IOC is started when the config is loaded,
        # restart means the IOC should automatically restart if it stops for some reason (e.g. it crashes)
        for n, ioc in self._active_configserver.get_all_ioc_details().iteritems():
            try:
                # If autostart is not set to True then the IOC is not part of the configuration
                if ioc.autostart:
                    # Throws if IOC does not exist
                    running = self._ioc_control.get_ioc_status(n)
                    if running == "RUNNING":
                        # Restart it
                        self._ioc_control.restart_ioc(n)
                    else:
                        # Start it
                        self._ioc_control.start_ioc(n)
            except Exception as err:
                print_and_log("Could not (re)start IOC %s: %s" % (n, str(err)), "MAJOR")

        # Give it time to start as IOC has to be running to be able to set restart property
        sleep(2)
        for n, ioc in self._active_configserver.get_all_ioc_details().iteritems():
            if ioc.autostart:
                # Set the restart property
                print_and_log("Setting IOC %s's auto-restart to %s" % (n, ioc.restart))
                self._ioc_control.set_autorestart(n, ioc.restart)

    def _get_iocs(self, include_running=False):
        # Get IOCs from DatabaseServer
        try:
            return self._db_client.get_iocs()
        except Exception as err:
            print_and_log("Could not retrieve IOC list: %s" % str(err), "MAJOR")
            return []

    def load_config(self, config, is_component=False):
        """Load a configuration.

        Args:
            config (string): The name of the configuration
            is_component (bool): Whether it is a component or not
        """
        try:
            if is_component:
                print_and_log("Loading component: %s" % config)
                self._active_configserver.load_active(config, True)
            else:
                print_and_log("Loading configuration: %s" % config)
                self._active_configserver.load_active(config)
            # If we get this far then assume the config is okay
            self._initialise_config(full_init=True)
        except Exception as err:
            print_and_log(str(err), "MAJOR")

    def reload_current_config(self):
        """Reload the current configuration."""
        try:
            print_and_log("Reloading current configuration")
            self._active_configserver.reload_current_config()
            # If we get this far then assume the config is okay
            self._initialise_config(full_init=True)
        except Exception as err:
            print_and_log(str(err), "MAJOR")

    def save_inactive_config(self, json_data, as_comp=False):
        """Save an inactive configuration.

        Args:
            json_data (string): The JSON data containing the configuration/component
            as_comp (bool): Whether it is a component or not
        """
        new_details = convert_from_json(json_data)
        inactive = InactiveConfigHolder(MACROS, self._vc, ConfigurationFileManager())

        history = self._get_inactive_history(new_details["name"], as_comp)

        inactive.set_config_details(new_details)

        # Set updated history
        history.append(self._get_timestamp())
        inactive.set_history(history)

        config_name = inactive.get_config_name()
        self._check_config_inactive(config_name, as_comp)
        try:
            if not as_comp:
                print_and_log("Saving configuration: %s" % config_name)
                inactive.save_inactive()
                self._config_list.update_a_config_in_list(inactive)
            else:
                print_and_log("Saving component: %s" % config_name)
                inactive.save_inactive(as_comp=True)
                self._config_list.update_a_config_in_list(inactive, True)
            print_and_log("Saved")
        except Exception as err:
            print_and_log("Problem occurred saving configuration: %s" % err)

        # Reload configuration if a component has changed
        if as_comp and new_details["name"] in self._active_configserver.get_component_names():
            self.load_last_config()

    def _get_inactive_history(self, name, is_component=False):
        # If it already exists load it
        try:
            inactive = InactiveConfigHolder(MACROS, self._vc, ConfigurationFileManager())
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
            name (string): The name to save it under
        """
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
        except Exception as err:
            print_and_log("Problem occurred saving configuration: %s" % err)

    def update_blocks_monitors(self):
        """Updates the monitors for the blocks and groups, so the clients can see any changes.
        """
        with self.monitor_lock:
            # Blocks
            bn = convert_to_json(self._active_configserver.get_blocknames())
            self.setParam(BlockserverPVNames.BLOCKNAMES, compress_and_hex(bn))
            # Groups
            # Update the PV, so that groupings are updated for any CA monitors
            grps = ConfigurationJsonConverter.groups_to_json(self._active_configserver.get_group_details())
            self.setParam(BlockserverPVNames.GROUPS, compress_and_hex(grps))
            # Update them
            self.updatePVs()

    def update_server_status(self, status=""):
        """Updates the monitor for the server status, so the clients can see any changes.

        Args:
            status (string): The status to set
        """
        if self._active_configserver is not None:
            d = dict()
            d['status'] = status
            with self.monitor_lock:
                self.setParam(BlockserverPVNames.SERVER_STATUS, compress_and_hex(convert_to_json(d)))
                self.updatePVs()

    def update_get_details_monitors(self):
        """Updates the monitor for the active configuration, so the clients can see any changes.
        """
        with self.monitor_lock:
            js = convert_to_json(self._active_configserver.get_config_details())
            self.setParam(BlockserverPVNames.GET_CURR_CONFIG_DETAILS, compress_and_hex(js))
            self.updatePVs()

    def update_bumpstrip_availability(self):
        """Updates the monitor for the configurations, so the clients can see any changes.
            """
        with self.monitor_lock:
            # set the available configs
            self.setParam(BlockserverPVNames.BUMPSTRIP_AVAILABLE, compress_and_hex(self.bumpstrip))
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
                if self._filewatcher is not None: self._filewatcher.pause()
                with self.write_lock:
                    cmd, arg, state = self.write_queue.pop(0)
                self.update_server_status(state)
                try:
                    if arg is not None:
                        cmd(*arg)
                    else:
                        cmd()
                except Exception as err:
                    print_and_log(
                        "Error executing write queue command %s for state %s: %s" % (cmd.__name__, state, err.message),
                        "MAJOR")
                self.update_server_status("")
                if self._filewatcher is not None: self._filewatcher.resume()
            sleep(1)

    def get_blank_config(self):
        """Get a blank configuration which can be used to create a new configuration from scratch.

        Returns:
            dict : A dictionary containing all the details of a blank configuration
        """
        temp_config = InactiveConfigHolder(MACROS, self._vc, ConfigurationFileManager())
        return temp_config.get_config_details()

    def _check_config_inactive(self, inactive_name, is_component=False):
        if not is_component:
            if inactive_name == self._active_configserver.get_config_name():
                raise ValueError("Cannot change config, use SET_CURR_CONFIG_DETAILS to change the active config")
        else:
            pass
            # TODO: check not a component of active, don't know what do to for this case?

    def start_iocs(self, iocs):
        # If the IOC is in the config and auto-restart is set to true then
        # reapply the auto-restart setting after starting.
        # This is because stopping an IOC via procServ turns auto-restart off.
        conf_iocs = self._active_configserver.get_all_ioc_details()

        # Request IOCs to start
        for i in iocs:
            self._ioc_control.start_ioc(i)

        # Once all IOC start requests issued, wait for running and apply auto restart as needed
        for i in iocs:
            if i in conf_iocs and conf_iocs[i].restart:
                # Give it time to start as IOC has to be running to be able to set restart property
                print "Re-applying auto-restart setting to %s" % i
                self._ioc_control.waitfor_running(i)
                self._ioc_control.set_autorestart(i, True)

    # Code for handling on-the-fly PVs
    def does_pv_exist(self, name):
        return name in manager.pvs[self.port]

    def delete_pv_from_db(self, name):
        if name in manager.pvs[self.port]:
            print_and_log("Removing PV %s" % name)
            fullname = manager.pvs[self.port][name].name
            del manager.pvs[self.port][name]
            del manager.pvf[fullname]
            del self.pvDB[name]
            del PVDB[name]

    def add_string_pv_to_db(self, name, count=1000):
        # Check name not already in PVDB and that a PV does not already exist
        if name not in PVDB and name not in manager.pvs[self.port]:
            try:
                print_and_log("Adding PV %s" % name)
                PVDB[name] = {
                    'type': 'char',
                    'count': count,
                    'value': [0],
                }
                self._cas.createPV(BLOCKSERVER_PREFIX, PVDB)
                # self.configure_pv_db()
                data = Data()
                data.value = manager.pvs[self.port][name].info.value
                self.pvDB[name] = data
            except Exception as err:
                print_and_log("Unable to add PV %S" % name,"MAJOR")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-cd', '--config_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration (default=current directory)')
    parser.add_argument('-sd', '--schema_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration schema (default=current directory)')
    parser.add_argument('-od', '--options_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration options(default=current directory)')
    parser.add_argument('-g', '--gateway_prefix', nargs=1, type=str, default=[MACROS["$(MYPVPREFIX)"] +
                                                                              'CS:GATEWAY:BLOCKSERVER'],
                        help='The prefix for the blocks gateway (default=' + MACROS[
                            "$(MYPVPREFIX)"] + 'CS:GATEWAY:BLOCKSERVER)')
    parser.add_argument('-pv', '--pvlist_name', nargs=1, type=str, default=['gwblock.pvlist'],
                        help='The filename for the pvlist file used by the blocks gateway (default=gwblock.pvlist)')
    parser.add_argument('-au', '--archive_uploader', nargs=1,
                        default=[os.path.join(MACROS["$(EPICS_KIT_ROOT)"], "CSS", "master", "ArchiveEngine",
                                              "set_block_config.bat")],
                        help='The batch file used to upload settings to the PV Archiver')
    parser.add_argument('-as', '--archive_settings', nargs=1,
                        default=[os.path.join(MACROS["$(EPICS_KIT_ROOT)"], "CSS", "master", "ArchiveEngine",
                                              "block_config.xml")],
                        help='The XML file containing the new PV Archiver log settings')
    parser.add_argument('-f', '--facility', nargs=1, type=str, default=['ISIS'],
                        help='Which facility is this being run for (default=ISIS)')

    args = parser.parse_args()

    FACILITY = args.facility[0]
    if FACILITY == "ISIS":
        from server_common.loggers.isis_logger import IsisLogger

        set_logger(IsisLogger())
    print_and_log("FACILITY = %s" % FACILITY)

    GATEWAY_PREFIX = args.gateway_prefix[0]
    if not GATEWAY_PREFIX.endswith(':'):
        GATEWAY_PREFIX += ":"
    GATEWAY_PREFIX = GATEWAY_PREFIX.replace('%MYPVPREFIX%', MACROS["$(MYPVPREFIX)"])
    print_and_log("BLOCK GATEWAY PREFIX = %s" % GATEWAY_PREFIX)

    CONFIG_DIR = os.path.abspath(args.config_dir[0])
    print_and_log("CONFIGURATION DIRECTORROOT_DIR %s" % CONFIG_DIR)

    SCHEMA_DIR = os.path.abspath(args.schema_dir[0])
    print_and_log("SCHEMA DIRECTORY = %s" % SCHEMA_DIR)

    ARCHIVE_UPLOADER = args.archive_uploader[0].replace('%EPICS_KIT_ROOT%', MACROS["$(EPICS_KIT_ROOT)"])
    print_and_log("ARCHIVE UPLOADER = %s" % ARCHIVE_UPLOADER)

    ARCHIVE_SETTINGS = args.archive_settings[0].replace('%EPICS_KIT_ROOT%', MACROS["$(EPICS_KIT_ROOT)"])
    print_and_log("ARCHIVE SETTINGS = %s" % ARCHIVE_SETTINGS)

    PVLIST_FILE = args.pvlist_name[0]

    print_and_log("BLOCKSERVER PREFIX = %s" % BLOCKSERVER_PREFIX)
    SERVER = SimpleServer()
    SERVER.createPV(BLOCKSERVER_PREFIX, PVDB)
    DRIVER = BlockServer(SERVER)

    # Process CA transactions
    while True:
        try:
            SERVER.process(0.1)
        except Exception as err:
            print_and_log(err,"MAJOR")
            break

