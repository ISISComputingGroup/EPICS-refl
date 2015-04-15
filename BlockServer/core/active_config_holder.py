import os
import json

from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.constants import RUNCONTROL_IOC, RUNCONTROL_SETTINGS, CONFIG_DIRECTORY, \
    COMPONENT_DIRECTORY
from BlockServer.core.runcontrol import RunControlManager
from server_common.utilities import print_and_log
from BlockServer.core.macros import BLOCKSERVER_PREFIX, BLOCK_PREFIX, MACROS
from BlockServer.core.config_holder import ConfigHolder


class ActiveConfigHolder(ConfigHolder):
    """Class to serve up the active configuration.
    """
    def __init__(self, config_folder, macros, archive_uploader, archive_config, vc_manager, ioc_control, test_mode=False):
        """ Constructor.

        Args:
            config_folder (string) : The location of the configurations folder
            macros (dict) : The BlockServer macros
            archive_uploader (string) : The location of the batch file for uploading the archiver settings
            archive_config (string) : The location to save the archive configuration folder
            test_mode (bool) : Whether to run in test mode
        """
        super(ActiveConfigHolder, self).__init__(config_folder, macros, vc_manager)
        self._archive_manager = ArchiverManager(archive_uploader, archive_config)
        self._ioc_control = ioc_control
        self._db = None
        self._last_config_file = os.path.abspath(config_folder + "/last_config.txt")
        self._runcontrol = RunControlManager(self._macros["$(MYPVPREFIX)"],
                                             self._macros["$(ICPCONFIGROOT)"] + RUNCONTROL_SETTINGS)
        self._test_mode = test_mode

        if not test_mode:
            # Start runcontrol IOC
            try:
                self._ioc_control.start_ioc(RUNCONTROL_IOC)
            except Exception as err:
                print_and_log("Problem with starting the run-control IOC: %s" % str(err), "MAJOR")
            # Need to wait for RUNCONTROL_IOC to (re)start
            print_and_log("Waiting for runcontrol IOC to (re)start")
            self._runcontrol.wait_for_ioc_start()
            print_and_log("Runcontrol IOC (re)started")

        if self._test_mode:
            self._set_testing_mode()

    def _set_testing_mode(self):
        self._archive_manager.set_testing_mode(True)
        from BlockServer.mocks.mock_runcontrol import MockRunControlManager
        self._runcontrol = MockRunControlManager()

    # Could we override save_configuration?
    def save_active(self, name, as_comp=False):
        """ Save the active configuration.

        Args:
            name (string) : The name to save the configuration under
            as_comp (bool) : Whether to save as a component
        """
        if as_comp:
            super(ActiveConfigHolder, self).save_configuration(name, as_comp)
            self.set_last_config(COMPONENT_DIRECTORY + name)
        else:
            super(ActiveConfigHolder, self).update_runcontrol_settings_for_saving(self.get_runcontrol_settings())
            super(ActiveConfigHolder, self).save_configuration(name, as_comp)
            self.set_last_config(CONFIG_DIRECTORY + name)

    # Could we override load_configuration?
    def load_active(self, name, is_subconfig=False):
        """ Load a configuration as the active configuration.

        Args:
            name (string) : The name of the configuration to load
            is_subconfig (bool) : Whether to it is a component
        """
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

    def update_archiver(self):
        """ Update the archiver configuration.
        """
        self._archive_manager.update_archiver(MACROS["$(MYPVPREFIX)"] + BLOCK_PREFIX, super(ActiveConfigHolder, self).get_blocknames())

    def set_last_config(self, config):
        """ Save the last configuration used to file.

        Args:
            config (string) : The name of the last configuration used
        """
        last = os.path.abspath(self._last_config_file)
        with open(last, 'w') as f:
            f.write(config + "\n")

    def load_last_config(self):
        """ Load the last used configuration.
        """
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
        """ Create the PVs for run-control.

        Configures the run-control IOC to have PVs for the current configuration.
        """
        self._runcontrol.update_runcontrol_blocks(super(ActiveConfigHolder, self).get_block_details())
        self._ioc_control.restart_ioc(RUNCONTROL_IOC)
        # Need to wait for RUNCONTROL_IOC to restart
        self._runcontrol.wait_for_ioc_start()

    def get_out_of_range_pvs(self):
        """ Returns the PVs that are out of range.

        Returns:
            list : A list of PVs that are out of range
        """
        return self._runcontrol.get_out_of_range_pvs()

    def get_runcontrol_settings(self):
        """ Returns the current run-control settings

        Returns:
            dict : The current run-control settings
        """
        return self._runcontrol.get_runcontrol_settings(super(ActiveConfigHolder, self).get_block_details())

    def set_runcontrol_settings(self, data):
        """ Replaces the runc-control settings with new values.

        Args:
            data (dict) : The new run-control settings to set
        """
        self._runcontrol.set_runcontrol_settings(data)

    def iocs_changed(self):
        """Checks to see if the IOCs have changed on saving."

        It checks for: IOCs added; IOCs removed; and, macros, pvs or pvsets changed.

        Returns:
            list, list : IOCs to start and IOCs to restart
        """
        iocs_to_start = list()
        iocs_to_restart = list()

        # Check to see if any macros, pvs, pvsets have changed
        for n in self._config.iocs.keys():
            if n not in self._cached_config.iocs.keys():
                # If not in previously then add it to start
                iocs_to_start.append(n)
                continue
            # Macros
            old_macros = self._cached_config.iocs[n].macros
            new_macros = self._config.iocs[n].macros
            if cmp(old_macros, new_macros) != 0:
                if n not in iocs_to_restart:
                    iocs_to_restart.append(n)
            # PVs
            old_pvs = self._cached_config.iocs[n].pvs
            new_pvs = self._config.iocs[n].pvs
            if cmp(old_pvs, new_pvs) != 0:
                if n not in iocs_to_restart:
                    iocs_to_restart.append(n)
            # Pvsets
            old_pvsets = self._cached_config.iocs[n].pvsets
            new_pvsets = self._config.iocs[n].pvsets
            if cmp(old_pvsets, new_pvsets) != 0:
                if n not in iocs_to_restart:
                    iocs_to_restart.append(n)
        return iocs_to_start, iocs_to_restart
