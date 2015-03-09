import os
import json

from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.constants import IOCS_NOT_TO_STOP, RUNCONTROL_IOC, RUNCONTROL_SETTINGS, CONFIG_DIRECTORY, \
    COMPONENT_DIRECTORY
from BlockServer.epics.procserv_utils import ProcServWrapper
from BlockServer.core.runcontrol import RunControlManager
from server_common.utilities import print_and_log
from BlockServer.core.database_server_client import DatabaseServerClient
from BlockServer.core.macros import BLOCKSERVER_PREFIX, BLOCK_PREFIX, MACROS
from BlockServer.core.config_holder import ConfigHolder


class ActiveConfigHolder(ConfigHolder):
    """Class to serve up the active config"""

    def __init__(self, config_folder, macros, archive_uploader, archive_config, test_mode=False):
        super(ActiveConfigHolder, self).__init__(config_folder, macros)
        self._archive_manager = ArchiverManager(archive_uploader, archive_config)
        self._procserve_wrapper = ProcServWrapper()
        self._db = None
        self._last_config_file = os.path.abspath(config_folder + "/last_config.txt")
        self._runcontrol = RunControlManager(self._macros["$(MYPVPREFIX)"],
                                             self._macros["$(ICPCONFIGROOT)"] + RUNCONTROL_SETTINGS)

        self._db_client = DatabaseServerClient(BLOCKSERVER_PREFIX)
        self._test_mode = test_mode

        if not test_mode:
            # Start runcontrol IOC
            try:
                self._procserve_wrapper.start_ioc(self._macros["$(MYPVPREFIX)"], RUNCONTROL_IOC)
            except Exception as err:
                print_and_log("Problem with starting the run-control IOC: %s" % err)
            # Need to wait for RUNCONTROL_IOC to (re)start
            print_and_log("Waiting for runcontrol IOC to (re)start")
            self._runcontrol.wait_for_ioc_start()
            print_and_log("Runcontrol IOC (re)started")

        if self._test_mode:
            self._set_testing_mode()

    def _set_testing_mode(self):
        self._archive_manager.set_testing_mode(True)
        from BlockServer.mocks.mock_procserv_utils import MockProcServWrapper
        self._procserve_wrapper = MockProcServWrapper()
        from BlockServer.mocks.mock_runcontrol import MockRunControlManager
        self._runcontrol = MockRunControlManager()

    # Could we override save_configuration?
    def save_active(self, name, as_comp=False):
        if as_comp:
            super(ActiveConfigHolder, self).save_configuration(name, as_comp)
            self.set_last_config(COMPONENT_DIRECTORY + name)
        else:
            super(ActiveConfigHolder, self).update_runcontrol_settings_for_saving(self.get_runcontrol_settings())
            super(ActiveConfigHolder, self).save_configuration(name, as_comp)
            self.set_last_config(CONFIG_DIRECTORY + name)

    # Could we override load_configuration?
    def load_active(self, name, is_subconfig=False):
        if is_subconfig:
            comp = super(ActiveConfigHolder, self).load_configuration(name, True)
            super(ActiveConfigHolder, self).set_config(comp, True)
            self.set_last_config(COMPONENT_DIRECTORY + name)
        else:
            conf = super(ActiveConfigHolder, self).load_configuration(name, False)
            super(ActiveConfigHolder, self).set_config(conf, False)
            self.set_last_config(CONFIG_DIRECTORY + name)
        self.create_runcontrol_pvs()
        self._runcontrol.restore_config_settings(super(ActiveConfigHolder, self).get_block_details())

    def get_ioc_state(self, ioc):
        return self._procserve_wrapper.get_ioc_status(self._macros["$(MYPVPREFIX)"], ioc)

    def start_iocs(self, data):
        for ioc in data:
            self._start_ioc(ioc)

    def _start_ioc(self, ioc):
        self._procserve_wrapper.start_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def _start_config_iocs(self):
        # Start the IOCs, if they are available and if they are flagged for autostart
        for n, ioc in super(ActiveConfigHolder, self).get_ioc_details().iteritems():
            try:
                # Throws if IOC does not exist
                # If it is already running restart it, otherwise start it
                running = self.get_ioc_state(n)
                if running == "RUNNING":
                    if ioc.restart:
                        self._restart_ioc(n)
                else:
                    if ioc.autostart:
                        self._start_ioc(n)
            except Exception as err:
                print_and_log("Could not (re)start IOC %s: %s" % (n, str(err)))

    def restart_iocs(self, data):
        for ioc in data:
            self._restart_ioc(ioc)

    def _restart_ioc(self, ioc):
        self._procserve_wrapper.restart_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def stop_iocs(self, data):
        for ioc in data:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self._stop_ioc(ioc)

    def _stop_ioc(self, ioc):
        self._procserve_wrapper.stop_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def stop_config_iocs(self):
        iocs = super(ActiveConfigHolder, self).get_ioc_names()
        self._stop_iocs(iocs)

    def stop_iocs_and_start_config_iocs(self):
        non_conf_iocs = [x for x in self._get_iocs() if x not in super(ActiveConfigHolder, self).get_ioc_names()]
        self._stop_iocs(non_conf_iocs)
        self._start_config_iocs()

    def _stop_iocs(self, iocs):
        iocs_to_stop = [x for x in iocs if not x.startswith(IOCS_NOT_TO_STOP)]
        for n in iocs_to_stop:
            try:
                # Throws if IOC does not exist
                running = self.get_ioc_state(n)
                if running == "RUNNING":
                    self._stop_ioc(n)
            except Exception as err:
                print_and_log("Could not stop IOC %s: %s" % (n, str(err)))

    def update_archiver(self):
        self._archive_manager.update_archiver(MACROS["$(MYPVPREFIX)"] + BLOCK_PREFIX, super(ActiveConfigHolder, self).get_blocknames())

    def _get_iocs(self, include_running=False):
        # Get IOCs from DatabaseServer
        try:
            return self._db_client.get_iocs()
        except Exception as err:
            print_and_log("Could not retrieve IOC list: %s" % str(err), "ERROR")
            return []

    def set_last_config(self, config):
        last = os.path.abspath(self._last_config_file)
        with open(last, 'w') as f:
            f.write(config + "\n")

    def load_last_config(self):
        last = os.path.abspath(self._last_config_file)
        if not os.path.isfile(last):
            return None
        with open(last, 'r') as f:
            last_config = f.readline().strip()
        if last_config.replace(COMPONENT_DIRECTORY, "").replace(CONFIG_DIRECTORY, "").strip() == "":
            print_and_log("No last configuration defined")
            return None
        if not self._test_mode:
            print_and_log("Trying to load last_configuration %s" % last_config)
        if last_config.startswith(COMPONENT_DIRECTORY):
            self.load_active(last_config.replace(COMPONENT_DIRECTORY, ""), True)
        else:
            self.load_active(last_config.replace(CONFIG_DIRECTORY, ""), False)
        return last_config

    def create_runcontrol_pvs(self):
        self._runcontrol.update_runcontrol_blocks(super(ActiveConfigHolder, self).get_block_details())
        self._procserve_wrapper.restart_ioc(self._macros["$(MYPVPREFIX)"], RUNCONTROL_IOC)
        # Need to wait for RUNCONTROL_IOC to restart
        self._runcontrol.wait_for_ioc_start()

    def get_out_of_range_pvs(self):
        return self._runcontrol.get_out_of_range_pvs()

    def get_runcontrol_settings(self):
        return self._runcontrol.get_runcontrol_settings(super(ActiveConfigHolder, self).get_block_details())

    def set_runcontrol_settings(self, data):
        self._runcontrol.set_runcontrol_settings(data)
