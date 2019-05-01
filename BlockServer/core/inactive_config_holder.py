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
from BlockServer.core.config_holder import ConfigHolder


class InactiveConfigHolder(ConfigHolder):
    """
    Class to hold a individual inactive configuration or component.
    """
    def __init__(self, macros, file_manager, test_config=None):
        """
        Constructor.

        Args:
            macros (dict): The BlockServer macros
            file_manager (ConfigurationFileManager): Deals with writing the config files
        """
        super(InactiveConfigHolder, self).__init__(macros, file_manager, test_config=test_config)

    def save_inactive(self, name=None, as_comp=False):
        """Saves a configuration or component that is not currently in use.

        Args:
            name (string): The name to save it under (defaults to the current config name)
            as_comp (bool): Whether to save it as a component (defaults to False)
        """
        if name is None:
            name = self.get_config_name()

        self.save_configuration(name, as_comp)

    def load_inactive(self, name, is_component=False):
        """
        Loads a configuration or component into memory for editing only.

        Args:
            name (string): The name of the configuration to load
            is_component (bool): Whether it is a component
        """
        config = self.load_configuration(name, is_component, False)
        self.set_config(config, is_component)

    def set_config_details(self, details):
        """ Set the details of the configuration from a dictionary.

        Args:
            details (dict): A dictionary containing the new configuration settings
        """
        self._cache_config()

        try:
            self.clear_config()
            if "iocs" in details:
                # List of dicts
                for ioc in details["iocs"]:
                    macros = self._to_dict(ioc.get('macros'))
                    pvs = self._to_dict(ioc.get('pvs'))
                    pvsets = self._to_dict(ioc.get('pvsets'))

                    if ioc.get('component') is not None:
                        raise ValueError('Cannot override iocs from components')

                    self._add_ioc(ioc['name'], autostart=ioc.get('autostart'), restart=ioc.get('restart'),
                                  macros=macros, pvs=pvs, pvsets=pvsets, simlevel=ioc.get('simlevel'))

            if "blocks" in details:
                # List of dicts
                for args in details["blocks"]:
                    if args.get('component') is not None:
                        raise ValueError('Cannot override blocks from components')
                    self.add_block(args)
            if "groups" in details:
                self._set_group_details(details["groups"])
            if "name" in details:
                self._set_config_name(details["name"])
            if "description" in details:
                self._config.meta.description = details["description"]
            if "synoptic" in details:
                self._config.meta.synoptic = details["synoptic"]
            # blockserver ignores history returned by clients:
            if "history" in details:
                self._config.meta.history = details["history"]
            if "components" in details:
                # List of dicts
                for args in details["components"]:
                    comp = self.load_configuration(args['name'], True)
                    self.add_component(comp.get_name(), comp)
        except Exception:
            self._retrieve_cache()
            raise
