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

import json

from BlockServer.core.config_holder import ConfigHolder


class InactiveConfigHolder(ConfigHolder):
    """ Class to hold a individual inactive configuration or component.
    """
    def __init__(self, macros, file_manager):
        """ Constructor.

        Args:
            macros (dict): The BlockServer macros
            file_manager (ConfigurationFileManager): Deals with writing the config files
        """
        super(InactiveConfigHolder, self).__init__(macros, file_manager)

    # Could we override save_configuration?
    def save_inactive(self, name=None, as_comp=False):
        """Saves a configuration or component that is not currently in use.

        Args:
            name (string): The name to save it under
            as_comp (bool): Whether to save it as a component
        """
        if name is None:
            name = super(InactiveConfigHolder, self).get_config_name()
        # See if comp or config already exists
        # if it does then load it
        super(InactiveConfigHolder, self).save_configuration(name, as_comp)

    # Could we override load_configuration?
    def load_inactive(self, name, is_component=False):
        """Loads a configuration or component into memory for editing only.

        Args:
            name (string): The name of the configuration to load
            is_component (bool): Whether it is a component
        """
        config = super(InactiveConfigHolder, self).load_configuration(name, is_component, False)
        super(InactiveConfigHolder, self).set_config(config, is_component)
