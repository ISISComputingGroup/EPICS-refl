import os
import json

from server_common.utilities import print_and_log
from BlockServer.core.macros import BLOCKSERVER_PREFIX, BLOCK_PREFIX, MACROS
from BlockServer.core.config_holder import ConfigHolder
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


class ActiveConfigHolder(ConfigHolder):
    """Class to serve up the active configuration.
    """
    def __init__(self, macros, archive_manager, vc_manager, ioc_control, run_control=None):
        """ Constructor.

        Args:
            macros (dict): The BlockServer macros
            archive_manager (ArchiveManager): Responsible for updating the archiver
            vc_manager (ConfigVersionControl): Manages version control
            ioc_control (IocControl): Manages stopping and starting IOCs
            run_control (RunControlManager): Manages run-control
        """
        super(ActiveConfigHolder, self).__init__(macros, vc_manager)
        self._archive_manager = archive_manager
        self._ioc_control = ioc_control
        self._db = None
        self._last_config_file = os.path.abspath(os.path.join(FILEPATH_MANAGER.config_root_dir, "last_config.txt"))
        self._runcontrol = run_control
        if run_control is not None:
            self._start_runcontrol()

    def _start_runcontrol(self):
        # Start runcontrol IOC
        self._runcontrol.start_ioc()
        # Need to wait for RUNCONTROL_IOC to start
        self._runcontrol.wait_for_ioc_start()
        print_and_log("Runcontrol IOC started")

    def save_active(self, name, as_comp=False):
        """ Save the active configuration.

        Args:
            name (string): The name to save the configuration under
            as_comp (bool): Whether to save as a component
        """
        if as_comp:
            super(ActiveConfigHolder, self).save_configuration(name, True)
        else:
            super(ActiveConfigHolder, self).save_configuration(name, False)
            self.set_last_config(name)

    def load_active(self, name):
        """ Load a configuration as the active configuration.
        Cannot load a component as the active configuration.

        Args:
            name (string): The name of the configuration to load
        """
        conf = super(ActiveConfigHolder, self).load_configuration(name, False)
        super(ActiveConfigHolder, self).set_config(conf, False)
        self.set_last_config(name)

    def update_archiver(self):
        """ Update the archiver configuration.
        """
        self._archive_manager.update_archiver(MACROS["$(MYPVPREFIX)"] + BLOCK_PREFIX,
                                              super(ActiveConfigHolder, self).get_block_details().values())

    def set_last_config(self, config):
        """ Save the last configuration used to file.

        The last configuration is saved without any file path.

        Args:
            config (string): The name of the last configuration used
        """
        last = os.path.abspath(self._last_config_file)
        with open(last, 'w') as f:
            f.write(config + "\n")

    def load_last_config(self):
        """ Load the last used configuration.

        The last configuration is saved without any file path.

        Note: should not be a component.
        """
        last = os.path.abspath(self._last_config_file)
        if not os.path.isfile(last):
            return None
        with open(last, 'r') as f:
            last_config = os.path.split(f.readline().strip())[-1]
            # Remove any legacy path separators
            last_config = last_config.replace("/", "")
            last_config = last_config.replace("\\", "")
        if last_config == "":
            print_and_log("No last configuration defined")
            return None
        print_and_log("Trying to load last_configuration %s" % last_config)
        self.load_active(last_config)
        return last_config

    def create_runcontrol_pvs(self, clear_autosave):
        """ Create the PVs for run-control.

        Configures the run-control IOC to have PVs for the current configuration.
        """
        if self._runcontrol is not None:
            self._runcontrol.update_runcontrol_blocks(super(ActiveConfigHolder, self).get_block_details())
            self._runcontrol.restart_ioc(clear_autosave)
            # Need to wait for RUNCONTROL_IOC to restart
            self._runcontrol.wait_for_ioc_start()
            self._runcontrol.restore_config_settings(super(ActiveConfigHolder, self).get_block_details())

    def get_out_of_range_pvs(self):
        """ Returns the PVs that are out of range.

        Returns:
            list : A list of PVs that are out of range
        """
        if self._runcontrol is not None:
            return self._runcontrol.get_out_of_range_pvs()
        else:
            return list()

    def get_runcontrol_settings(self):
        """ Returns the current run-control settings

        Returns:
            dict : The current run-control settings
        """
        if self._runcontrol is not None:
            return self._runcontrol.get_current_settings(super(ActiveConfigHolder, self).get_block_details())
        else:
            return dict()

    def set_runcontrol_settings(self, data):
        """ Replaces the run-control settings with new values.

        Args:
            data (dict): The new run-control settings to set
        """
        if self._runcontrol is not None:
            self._runcontrol.set_runcontrol_settings(data)

    def iocs_changed(self):
        """Checks to see if the IOCs have changed on saving."

        It checks for: IOCs added; IOCs removed; and, macros, pvs or pvsets changed.

        Returns:
            set, set : IOCs to start and IOCs to restart
        """
        iocs_to_start = list()
        iocs_to_restart = list()

        # Check to see if any macros, pvs, pvsets etc. have changed
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
            # Auto-restart changed
            if n in self._cached_config.iocs.keys() and \
                            self._config.iocs[n].restart != self._cached_config.iocs[n].restart:
                # If not in previously then add it to start
                iocs_to_restart.append(n)
                continue

        # Look for any new components
        for cn, cv in self._components.iteritems():
            if cn not in self._cached_components:
                for n in cv.iocs.keys():
                    iocs_to_start.append(n)

        return set(iocs_to_start), set(iocs_to_restart)
