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
import json

from server_common.utilities import print_and_log
from BlockServer.core.macros import BLOCK_PREFIX, MACROS
from BlockServer.core.config_holder import ConfigHolder
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


class ActiveConfigHolder(ConfigHolder):
    """Class to serve up the active configuration.
    """
    def __init__(self, macros, archive_manager, vc_manager, file_manager, ioc_control):
        """ Constructor.

        Args:
            macros (dict): The BlockServer macros
            archive_manager (ArchiveManager): Responsible for updating the archiver
            vc_manager (ConfigVersionControl): Manages version control
            file_manager (ConfigurationFileManager): Deals with writing the config files
            ioc_control (IocControl): Manages stopping and starting IOCs
        """
        super(ActiveConfigHolder, self).__init__(macros, vc_manager, file_manager)
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
