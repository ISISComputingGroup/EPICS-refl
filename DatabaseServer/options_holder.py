from __future__ import print_function, absolute_import, division, unicode_literals
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
import six
from DatabaseServer.options_loader import OptionsLoader


class OptionsHolder(object):
    """Holds all the IOC options"""
    def __init__(self, options_folder: str, options_loader: OptionsLoader):
        """Constructor

        Args:
            options_folder: The path of the directory holding the config.xml file
            options_loader: An instance of OptionsLoader to load options from file
        """
        self._config_options = options_loader.get_options(options_folder + '/config.xml')

    def get_config_options(self) -> dict:
        """Converts all stored IocOptions into dicts

        Returns:
            IOCs and their associated options as a dictionary
        """
        return {name: options.to_dict() for name, options in six.iteritems(self._config_options)}
