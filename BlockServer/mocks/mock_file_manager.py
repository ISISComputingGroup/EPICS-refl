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
from BlockServer.config.configuration import Configuration


class MockConfigurationFileManager(object):

    def __init__(self):
        self.confs = dict()
        self.comps = dict()
        # Add the standard base config
        base = Configuration(None)
        base.set_name("_base")
        self.comps["_base"] = base
        self._load_config_requests = list()

    def find_ci(self, root_path, name):
        """Find a file with a case insensitive match"""
        res = ''
        for f in os.listdir(root_path):
            if f.lower() == name.lower():
                res = f
        return res

    def load_config(self, name, macros, is_component):
        self._load_config_requests.append(name)
        if is_component:
            if name.lower() not in self.comps:
                raise IOError("Component could not be found: " + name)

            return self.comps[name.lower()]
        else:
            if name.lower() not in self.confs:
                raise IOError("Configuration could not be found: " + name)

            return self.confs[name.lower()]

    def save_config(self, configuration, is_component):
        # Just keep the config in memory
        if is_component:
            self.comps[configuration.get_name().lower()] = configuration
        else:
            self.confs[configuration.get_name().lower()] = configuration

    def delete(self, name, is_component):
        if is_component:
            del self.comps[name.lower()]
        else:
            del self.confs[name.lower()]

    def component_exists(self, root_path, name):
        if name.lower() not in self.confs:
            raise Exception("Component does not exist")

    def copy_default(self, dest_path):
        pass

    def get_files_in_directory(self, path):
        return list()

    def get_load_config_history(self):
        return self._load_config_requests
