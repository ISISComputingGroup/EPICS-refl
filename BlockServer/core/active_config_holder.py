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
import os
import six

from server_common.utilities import print_and_log
from BlockServer.core.macros import BLOCK_PREFIX, MACROS
from BlockServer.core.config_holder import ConfigHolder
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


class ActiveConfigHolder(ConfigHolder):
    """
    Class to serve up the active configuration.
    """
    def __init__(self, macros, archive_manager, file_manager, ioc_control):
        """ Constructor.

        Args:
            macros (dict): The BlockServer macros
            archive_manager (ArchiverManager): Responsible for updating the archiver
            file_manager (ConfigurationFileManager|MockVersionControl): Deals with writing the config files
            ioc_control (IocControl): Manages stopping and starting IOCs
        """
        super(ActiveConfigHolder, self).__init__(macros, file_manager)
        self._archive_manager = archive_manager
        self._ioc_control = ioc_control
        self._db = None
        self._last_config_file = os.path.abspath(os.path.join(FILEPATH_MANAGER.config_root_dir, "last_config.txt"))

    def save_active(self, name, as_comp=False):
        """ Save the active configuration.

        Args:
            name (string): The name to save the configuration under
            as_comp (bool): Whether to save as a component
        """
        if as_comp:
            self.save_configuration(name, True)
        else:
            self.save_configuration(name, False)
            self.set_last_config(name)

    def load_active(self, name):
        """ Load a configuration as the active configuration.
        Cannot load a component as the active configuration.

        Args:
            name (string): The name of the configuration to load
        """
        self.set_config(self.load_configuration(name))
        self.set_last_config(name)

    def update_archiver(self, full_init=False):
        """ Update the archiver configuration.

        Args:
            full_init: if True restart; if False only restart if blocks have changed
        """
        if full_init or self.blocks_changed():
            self._archive_manager.update_archiver(MACROS["$(MYPVPREFIX)"] + BLOCK_PREFIX,
                                                  self.get_block_details().values())

    def set_last_config(self, config):
        """ Save the last configuration used to file.

        The last configuration is saved without any file path.

        Args:
            config (string): The name of the last configuration used
        """
        with open(os.path.abspath(self._last_config_file), 'w') as f:
            f.write(config + "\n")

    def load_last_config(self):
        """ Load the last used configuration.

        The last configuration is saved without any file path.

        Note: should not be a component.

        Returns:
            The name of the configuration that was loaded
        """
        last_config_file_location = os.path.abspath(self._last_config_file)

        if not os.path.isfile(last_config_file_location):
            return None

        with open(last_config_file_location) as f:
            last_config_name = os.path.split(f.readline().strip())[-1]
            # Remove any legacy path separators
            last_config_name = last_config_name.replace("/", "")
            last_config_name = last_config_name.replace("\\", "")

        if last_config_name == "":
            print_and_log("No last configuration defined")
            return None

        print_and_log("Trying to load last configuration '{}'".format(last_config_name))
        self.load_active(last_config_name)
        return last_config_name

    def reload_current_config(self):
        """ Reload the current configuration."""
        current_config_name = self.get_config_name()
        if current_config_name == "":
            print_and_log("No current configuration defined. Nothing to reload.")
            return

        print_and_log("Trying to reload current configuration '{}'".format(current_config_name))
        self.load_active(current_config_name)

    def _compare_ioc_properties(self, old, new):
        """
        Compares the properties of IOCs in a component/configuration.

        Args:
            old: The component or configuration to use as a baseline when comparing IOCs
            new: The corresponding new configuration or component

        Returns:
            set, set, set : IOCs to start, IOCs to restart, IOCs to stop.
        """
        iocs_to_start = set()
        iocs_to_restart = set()
        iocs_to_stop = set()

        _attributes = ["macros", "pvs", "pvsets", "simlevel", "restart"]

        for ioc_name in new.iocs.keys():
            if ioc_name not in old.iocs.keys():
                # If not in previously then add it to start
                iocs_to_start.add(ioc_name)
            elif any(getattr(old.iocs[ioc_name], attr) != getattr(new.iocs[ioc_name], attr) for attr in _attributes):
                # If any attributes have changed, restart the IOC
                iocs_to_restart.add(ioc_name)

        return iocs_to_start, iocs_to_restart, iocs_to_stop

    def iocs_changed(self):
        """Checks to see if the IOCs have changed on saving."

        It checks for: IOCs added; IOCs removed; and, macros, pvs or pvsets changed.

        Returns:
            set, set, set : IOCs to start, IOCs to restart, IOCs to stop.
        """
        iocs_to_start, iocs_to_restart, iocs_to_stop = self._compare_ioc_properties(self._cached_config, self._config)

        # Look for any new components
        for name, component in six.iteritems(self._components):
            if name in self._cached_components:
                _start, _restart, _stop = \
                    self._compare_ioc_properties(self._cached_components[name], self._components[name])

                iocs_to_start |= _start
                iocs_to_restart |= _restart
                iocs_to_stop |= _stop
            else:
                for ioc_name in component.iocs.keys():
                    iocs_to_start.add(ioc_name)

        # Look for any removed components
        for name, component in six.iteritems(self._cached_components):
            if name not in self._components:
                for ioc_name in component.iocs.keys():
                    iocs_to_stop.add(ioc_name)

        return iocs_to_start, iocs_to_restart, iocs_to_stop

    def _blocks_in_top_level_config_changed(self):
        """
        Checks whether the blocks in the top level configuration have changed

        Returns:
            True if the blocks have changed, False otherwise
        """
        for n in self._config.blocks.keys():
            # Check to see if there are any new blocks
            if n not in self._cached_config.blocks.keys():
                # If not in previously then blocks have been added changed
                return True

            cached_block = self._cached_config.blocks[n].to_dict()
            current_block = self._config.blocks[n].to_dict()
            # Check for any changed blocks (symmetric difference operation of sets)
            block_diff = set(cached_block.items()) ^ set(current_block.items())
            if len(block_diff) != 0:
                return True

        return False

    def _blocks_removed_from_top_level_config(self):
        """
        Checks whether any blocks have been removed from the top level configuration (does not recurse to components)

        Returns:
            True if blocks have been removed from the top-level config; False otherwise
        """
        return any(name not in self._config.blocks for name in self._cached_config.blocks)

    @staticmethod
    def _check_for_added_blocks(old_components, new_components):
        """
        Checks whether there are any new blocks when moving between two sets of components.

        Args:
            old_components (dict): Dictionary of components in the form {component_name: component, ...}
            new_components (dict): Dictionary of components in the form {component_name: component, ...}

        Returns:
            True if switching from components1 to components2 would have added any blocks.
        """
        for new_component_name, new_component in new_components.iteritems():
            if new_component_name not in old_components and len(new_component.blocks) != 0:
                return True
        return False

    def _new_components_containing_blocks(self):
        """
        Checks whether there are any new components which contain blocks.

        Returns:
            True if there are new components with blocks defined, False otherwise
        """
        return ActiveConfigHolder._check_for_added_blocks(self._cached_components, self._components)

    def _removed_components_containing_blocks(self):
        """
        Checks whether there are any removed components which contained blocks.

        Returns:
            True if there are removed components with blocks defined, False otherwise
        """

        # Check for removed blocks == check for added blocks in the other direction.
        return ActiveConfigHolder._check_for_added_blocks(self._components, self._cached_components)

    def blocks_changed(self):
        """
        Checks to see if the Blocks have changed on saving."

        It checks for: Blocks added; Blocks removed; Blocks changed; New components

        Returns:
            bool : True if blocks have changed, False otherwise
        """
        return self._blocks_in_top_level_config_changed() \
            or self._blocks_removed_from_top_level_config() \
            or self._new_components_containing_blocks() \
            or self._removed_components_containing_blocks()
