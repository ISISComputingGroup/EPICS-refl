"""
Manager to capture file paths within the ibex system.
"""
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

CONFIG_DIRECTORY = "configurations"
COMPONENT_DIRECTORY = "components"
SYNOPTIC_DIRECTORY = "synoptics"
DEVICES_DIRECTORY = "devices"


# Do not create an instance of this class, instead use FILEPATH_MANAGER as a singleton
class FilePathManager(object):
    """
    Manager for file paths
    """

    def __init__(self):
        self.config_root_dir = ""
        self.config_dir = ""
        self.component_dir = ""
        self.synoptic_dir = ""
        self.schema_dir = ""
        self.devices_dir = ""
        self.scripts_dir = ""

    def initialise(self, config_root, scripts_root, schema_folder):
        """
        Init.
        Args:
            config_root: configuration root directory
            scripts_root: script root directory
            schema_folder: folder for the xml schema
        """
        self.config_root_dir = config_root
        self.schema_dir = os.path.abspath(schema_folder)
        self.config_dir = os.path.join(config_root, CONFIG_DIRECTORY)
        self.component_dir = os.path.join(config_root, COMPONENT_DIRECTORY)
        self.synoptic_dir = os.path.join(config_root, SYNOPTIC_DIRECTORY)
        self.devices_dir = os.path.join(config_root, DEVICES_DIRECTORY)
        self.scripts_dir = scripts_root
        self._create_default_folders()

    def _create_default_folders(self):
        # Create default folders
        paths = [self.config_root_dir, self.config_dir, self.component_dir, self.synoptic_dir, self.devices_dir]
        for p in paths:
            if not os.path.isdir(p):
                # Create it then
                os.makedirs(os.path.abspath(p))

    def get_component_path(self, component_name):
        """
        Args:
            component_name: the component name

        Returns: The full path to the directory of the named component

        """
        return os.path.abspath(os.path.join(self.component_dir, component_name))

    def get_config_path(self, config_name):
        """
        Args:
            config_name: the configurations name

        Returns: The full path to the directory of the named configuration

        """
        return os.path.abspath(os.path.join(self.config_dir, config_name))

    def get_synoptic_path(self, synoptic_name):
        """

        Args:
            synoptic_name: name of the synoptic

        Returns: File path to the synoptic of the given name

        """
        return os.path.join(self.synoptic_dir, "{}.xml".format(synoptic_name))

    def get_banner_path(self):
        """
        Returns: the file path to the banner definition file. The banner is the information bar at the bottom of the gui

        """
        return os.path.join(self.config_root_dir, "banner.xml")

    def get_last_config_file_path(self):
        """
        Returns: File path of the last config file, this is the file which indicates the last configuration that was
        loaded by the block server (this should be the current config)

        """
        return os.path.abspath(os.path.join(FILEPATH_MANAGER.config_root_dir, "last_config.txt"))


# This is the singleton to use
FILEPATH_MANAGER = FilePathManager()
