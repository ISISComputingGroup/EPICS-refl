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
import re
import os
import shutil
from collections import OrderedDict
from xml.etree import ElementTree

from BlockServer.config.group import Group
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.config.configuration import Configuration, MetaData
from BlockServer.core.constants import FILENAME_BLOCKS, FILENAME_GROUPS, FILENAME_IOCS, FILENAME_COMPONENTS, \
    FILENAME_META
from BlockServer.core.constants import GRP_NONE, DEFAULT_COMPONENT, EXAMPLE_DEFAULT
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker, ConfigurationIncompleteException
from server_common.utilities import print_and_log, retry
from server_common.common_exceptions import MaxAttemptsExceededException

RETRY_MAX_ATTEMPTS = 20
RETRY_INTERVAL = 0.5


class ConfigurationFileManager(object):
    """ The ConfigurationFileManager class.

    Contains utilities to save and load configurations.
    """

    def find_ci(self, root_path, name):
        """find a file with a case insensitive match"""
        res = ''
        for f in os.listdir(root_path):
            if f.lower() == name.lower():
                res = f
        return res

    def load_config(self, name, macros, is_component):
        """Loads the configuration from the specified folder.

        Args:
            name (string): The name of the configuration
            macros (dict): The BlockServer macros
            is_component (bool): Is it a component?
        """
        print_and_log("Start loading config...")
        configuration = Configuration(macros)

        path = self.get_path(name, is_component)

        if not os.path.isdir(path):
            raise IOError("Configuration could not be found: " + name)

        # Create empty containers
        blocks = OrderedDict()
        groups = OrderedDict()
        components = OrderedDict()
        iocs = OrderedDict()

        # Make sure NONE group exists
        groups[GRP_NONE.lower()] = Group(GRP_NONE)

        config_files_missing = list()

        # Open the block file first
        blocks_path = os.path.join(path, FILENAME_BLOCKS)
        if os.path.isfile(blocks_path):
            root = self._read_element_tree(blocks_path)

            # Check against the schema - raises if incorrect
            self._check_againgst_schema(ElementTree.tostring(root, encoding='utf8'), FILENAME_BLOCKS)

            ConfigurationXmlConverter.blocks_from_xml(root, blocks, groups)
        else:
            config_files_missing.append(FILENAME_BLOCKS)

        # Import the groups
        groups_path = os.path.join(path, FILENAME_GROUPS)
        if os.path.isfile(groups_path):
            root = self._read_element_tree(groups_path)

            # Check against the schema - raises if incorrect
            self._check_againgst_schema(ElementTree.tostring(root, encoding='utf8'), FILENAME_GROUPS)

            ConfigurationXmlConverter.groups_from_xml(root, groups, blocks)
        else:
            config_files_missing.append(FILENAME_GROUPS)

        # Import the IOCs
        iocs_path = os.path.join(path, FILENAME_IOCS)
        if os.path.isfile(iocs_path):
            root = self._read_element_tree(iocs_path)

            # There was a historic bug where the simlevel was saved as 'None' rather than "none".
            # Correct that here
            correct_xml = ElementTree.tostring(root, encoding='utf8').replace('simlevel="None"',
                                                                              'simlevel="none"')

            # Check against the schema - raises if incorrect
            self._check_againgst_schema(correct_xml, FILENAME_IOCS)

            ConfigurationXmlConverter.ioc_from_xml(root, iocs)
        else:
            config_files_missing.append(FILENAME_IOCS)

        # Import the components
        component_path = os.path.join(path, FILENAME_COMPONENTS)
        if os.path.isfile(component_path):
            root = self._read_element_tree(component_path)

            # Check against the schema - raises if incorrect
            self._check_againgst_schema(ElementTree.tostring(root, encoding='utf8'), FILENAME_COMPONENTS)

            ConfigurationXmlConverter.components_from_xml(root, components)
        elif not is_component:
            # It should be missing for a component
            config_files_missing.append(FILENAME_COMPONENTS)

        # Import the metadata
        meta = MetaData(name)
        meta_path = os.path.join(path, FILENAME_META)
        if os.path.isfile(meta_path):
            root = self._read_element_tree(meta_path)

            # Check against the schema - raises if incorrect
            self._check_againgst_schema(ElementTree.tostring(root, encoding='utf8'), FILENAME_META)

            ConfigurationXmlConverter.meta_from_xml(root, meta)
        else:
            config_files_missing.append(FILENAME_META)

        if len(config_files_missing) > 0:
            raise ConfigurationIncompleteException("Files missing in " + name +
                                                   " (%s)" % ','.join(list(config_files_missing)))

        # Set properties in the config
        configuration.blocks = blocks
        configuration.groups = groups
        configuration.iocs = iocs
        configuration.components = components
        configuration.meta = meta
        print_and_log("Archive Access Configuration loaded.")
        return configuration

    def _check_againgst_schema(self, xml, filename):
        regex = re.compile(re.escape('.xml'), re.IGNORECASE)
        name = regex.sub('.xsd', filename)
        schema_path = os.path.join(FILEPATH_MANAGER.schema_dir, name)
        ConfigurationSchemaChecker.check_xml_data_matches_schema(schema_path, xml)

    def save_config(self, configuration, is_component):
        """Saves the current configuration with the specified name.

        Args:
            configuration (Configuration): The actual configuration to save
            is_component (bool): Is it a component?
        """
        path = self.get_path(configuration.get_name(), is_component)

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
        current_file = os.path.join(path, FILENAME_BLOCKS)
        self._write_to_file(current_file, blocks_xml)

        # Save groups
        current_file = os.path.join(path, FILENAME_GROUPS)
        self._write_to_file(current_file, groups_xml)

        # Save IOCs
        current_file = os.path.join(path, FILENAME_IOCS)
        self._write_to_file(current_file, iocs_xml)

        # Save components
        current_file = os.path.join(path, FILENAME_COMPONENTS)
        self._write_to_file(current_file, components_xml)

        # Save meta
        current_file = os.path.join(path, FILENAME_META)
        self._write_to_file(current_file, meta_xml)

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def delete(self, name, is_component):
        path = self.get_path(name, is_component)
        if not os.path.exists(path):
            print_and_log("Directory {path} not found on filesystem.".format(path=path), "MINOR")
            return
        shutil.rmtree(path)

    def component_exists(self, root_path, name):
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
                        os.path.join(dest_path, DEFAULT_COMPONENT))

    def _read_element_tree(self, file_path):
        try:
            return self._attempt_read(file_path)
        except MaxAttemptsExceededException:
            raise IOError("Could not open file at {path}. Please check the file "
                          "is not in use by another process.".format(path=file_path))

    def _write_to_file(self, file_path, data):
        try:
            return self._attempt_write(file_path, data)
        except MaxAttemptsExceededException:
            raise IOError("Could not write to file at {path}. Please check the file is "
                          "not in use by another process.".format(path=file_path))

    @staticmethod
    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def _attempt_read(file_path):
        """ Read and return the element tree from a given xml file.

        Args:
            file_path (string): The location of the file being read
        """
        return ElementTree.parse(file_path).getroot()

    @staticmethod
    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def _attempt_write(file_path, data):
        """ Write xml data to a given configuration file.

        Args:
            file_path (string): The location of the file being written
            data (string): The XML data to be saved
        """
        with open(file_path, 'w') as f:
            f.write(data)
            return

    def get_files_in_directory(self, path):
        """Gets a list of the files in the specified folder

        Args:
            path (string): The path of the folder

        Returns:
            list: the files in the folder
        """
        files = list()
        if os.path.isdir(path):
            files = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return files

    @staticmethod
    def get_path(name, is_component):
        if is_component:
            path = os.path.abspath(FILEPATH_MANAGER.get_component_path(name))
        else:
            path = os.path.abspath(FILEPATH_MANAGER.get_config_path(name))

        return path
