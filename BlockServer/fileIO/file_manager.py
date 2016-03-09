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

import os
import shutil
from collections import OrderedDict

from server_common.utilities import parse_xml_removing_namespace, print_and_log
from BlockServer.config.containers import Group
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.config.configuration import Configuration, MetaData
from config_version_control import ConfigVersionControl
from vc_exceptions import NotUnderVersionControl
from BlockServer.core.constants import FILENAME_BLOCKS, FILENAME_GROUPS, FILENAME_IOCS, FILENAME_COMPONENTS, FILENAME_META
from BlockServer.core.constants import GRP_NONE, DEFAULT_COMPONENT, EXAMPLE_DEFAULT


class ConfigurationFileManager(object):
    """ The ConfigurationFileManager class.

    Contains utilities to save and load configurations and to communicate with the version control system.
    """

    @staticmethod
    def find_ci(root_path, name):
        """find a file with a case insensitive match"""
        res = ''
        for f in os.listdir(root_path):
            if f.lower() == name.lower():
                res = f
        return res
    
    @staticmethod
    def load_config(config_folder, name, macros):
        """Loads the configuration from the specified folder.

        Args:
            config_folder (string): The configuration's folder
            name (string): The name of the configuration
            macros (dict): The BlockServer macros
        """
        configuration = Configuration(macros)

        if not os.path.isdir(config_folder):
            raise IOError("Configuration could not be found: " + name)

        # Create empty containers
        blocks = OrderedDict()
        groups = OrderedDict()
        components = OrderedDict()
        iocs = OrderedDict()

        # Make sure NONE group exists
        groups[GRP_NONE.lower()] = Group(GRP_NONE)

        # Open the block file first
        blocks_path = config_folder + "/" + FILENAME_BLOCKS
        if os.path.isfile(blocks_path):
            root = parse_xml_removing_namespace(blocks_path)
            ConfigurationXmlConverter.blocks_from_xml(root, blocks, groups)

        # Import the groups
        groups_path = config_folder + "/" + FILENAME_GROUPS
        if os.path.isfile(groups_path):
            root = parse_xml_removing_namespace(groups_path)
            ConfigurationXmlConverter.groups_from_xml(root, groups, blocks)

        # Import the IOCs
        iocs_path = config_folder + "/" + FILENAME_IOCS
        if os.path.isfile(iocs_path):
            root = parse_xml_removing_namespace(iocs_path)
            ConfigurationXmlConverter.ioc_from_xml(root, iocs)

        # Import the components
        component_path = config_folder + "/" + FILENAME_COMPONENTS
        if os.path.isfile(component_path):
            root = parse_xml_removing_namespace(component_path)
            ConfigurationXmlConverter.components_from_xml(root, components)

        # Import the metadata
        meta = MetaData(name)
        meta_path = config_folder + '/' + FILENAME_META
        if os.path.isfile(meta_path):
            root = parse_xml_removing_namespace(meta_path)
            ConfigurationXmlConverter.meta_from_xml(root, meta)

        # Set properties in the config
        configuration.blocks = blocks
        configuration.groups = groups
        configuration.iocs = iocs
        configuration.components = components
        configuration.meta = meta
        return configuration

    @staticmethod
    def save_config(configuration, config_folder):
        """Saves the current configuration with the specified name.

        Args:
            configuration (Configuration): The actual configuration to save
            config_folder (string): The configuration's folder
        """
        path = os.path.abspath(config_folder)
        if not os.path.isdir(path):
            # Create the directory
            os.makedirs(path)

        blocks_xml = ConfigurationXmlConverter.blocks_to_xml(configuration.blocks, configuration.macros)
        groups_xml = ConfigurationXmlConverter.groups_to_xml(configuration.groups)
        iocs_xml = ConfigurationXmlConverter.iocs_to_xml(configuration.iocs)
        meta_xml = ConfigurationXmlConverter.meta_to_xml(configuration.meta)
        try:
            components_xml = ConfigurationXmlConverter.components_to_xml(configuration.components)
        except:
            # Is a component, so no components
            components_xml = ConfigurationXmlConverter.components_to_xml(dict())

        # Save blocks
        with open(path + '/' + FILENAME_BLOCKS, 'w') as f:
            f.write(blocks_xml)

        # Save groups
        with open(path + '/' + FILENAME_GROUPS, 'w') as f:
            f.write(groups_xml)

        # Save IOCs
        with open(path + '/' + FILENAME_IOCS, 'w') as f:
            f.write(iocs_xml)

        # Save components
        with open(path + '/' + FILENAME_COMPONENTS, 'w') as f:
            f.write(components_xml)

        # Save meta
        with open(path + '/' + FILENAME_META, 'w') as f:
            f.write(meta_xml)

    @staticmethod
    def component_exists(root_path, name):
        """Checks to see if a component exists.

        root_path (string): The root folder where components are stored
        name (string): The name of the components

        Raises:
            (Exception): raises an Exception if the component does not exist
        """
        if not os.path.isdir(os.path.join(root_path, name)):
            raise Exception("Component does not exist")

    @staticmethod
    def copy_default(dest_path):
        """Copies the default/base component in if it does exist.

        Args:
            dest_path (string): The root folder where configurations are stored
        """
        shutil.copytree(os.path.abspath(os.path.join(os.environ["MYDIRBLOCK"], EXAMPLE_DEFAULT)),
                        os.path.join(dest_path,DEFAULT_COMPONENT))
