#This file is part of the ISIS IBEX application.
#Copyright (C) 2012-2016 Science & Technology Facilities Council.
#All rights reserved.
#
#This program is distributed in the hope that it will be useful.
#This program and the accompanying materials are made available under the
#terms of the Eclipse Public License v1.0 which accompanies this distribution.
#EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
#AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
#OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
#You should have received a copy of the Eclipse Public License v1.0
#along with this program; if not, you can obtain a copy from
#https://www.eclipse.org/org/documents/epl-v10.php or 
#http://opensource.org/licenses/eclipse-1.0.php

from collections import OrderedDict

from BlockServer.core.constants import GRP_NONE
from BlockServer.config.xml_converter import ConfigurationXmlConverter


class MockConfiguration(object):
    def __init__(self):
        # variables set when the class under test calls mock functions to be read by the testing code
        self.add_block_called = False
        self.remove_block_called = False
        self.edit_block_called = False
        self.add_block_parameters = []
        self.remove_block_parameters = []
        self.edit_block_parameters = []
        # variables set by the testing code to be fed to the class under test when it calls mock functions
        self.block_names = []
        self.blocks = OrderedDict()

    def add_block(self, name, read_pv, group=GRP_NONE, local=True, visible=True,
                  log_periodic=False, log_rate=5, log_deadband=0):
        self.add_block_called = True
        self.add_block_parameters = [name, read_pv, group, local, visible, log_periodic, log_rate, log_deadband]

    def remove_block(self, name):
        self.remove_block_called = True
        self.remove_block_parameters = [name]

    def edit_block(self, name, read_pv, group, local, new_name=None):
        self.edit_block_called = True
        self.edit_block_parameters = [name, read_pv, group, local, new_name]

    def get_block_names(self):
        return self.block_names


class MockConfigurationFileManager(object):
    def __init__(self):
        self.blocks_xml = ""
        self.groups_xml = ""
        self.iocs_xml = ""
        self.components_xml = ""

    @staticmethod
    def load_config(configuration, root_path, config_name):
        pass

    def save_config(self, configuration, root_path, config_name):
        self.blocks_xml = ConfigurationXmlConverter.blocks_to_xml(configuration.blocks, configuration.macros)
        self.groups_xml = ConfigurationXmlConverter.groups_to_xml(configuration.groups)
        self.iocs_xml = ConfigurationXmlConverter.iocs_to_xml(configuration.iocs)
        self.components_xml = ConfigurationXmlConverter.components_to_xml(configuration.components)


class MockConfigurationXmlConverter(object):
    def __init__(self):
        self.blocks_xml = ""
        self.groups_xml = ""
        self.iocs_xml = ""
        self.components_xml = ""

    def blocks_to_xml(self, blocks, macros):
        return self.blocks_xml

    def groups_to_xml(self, groups, include_none=False):
        return self.groups_xml

    def iocs_to_xml(self, iocs):
        return self.iocs_xml

    def components_to_xml(self, components):
        return self.components_xml

    @staticmethod
    def groups_from_xml(xml, groups, blocks):
        pass

    @staticmethod
    def groups_from_xml_string(root_xml, groups, blocks):
        pass


class MockConfigurationJsonConverter(object):
    def __init__(self):
        self.blocks_json = ""

    def blocks_to_json(self, blocks, pv_prefix):
        return self.blocks_json

    def groups_from_json(self, js, groups):
        pass
