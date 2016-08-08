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

import unittest
import os
from BlockServer.core.file_path_manager import FILEPATH_MANAGER, CONFIG_DIRECTORY, COMPONENT_DIRECTORY, \
    SYNOPTIC_DIRECTORY

CONFIG_PATH = "./test_configs/"
SCHEMA_FOLDER = "schema"


class TestFilePathManagerSequence(unittest.TestCase):
    def setUp(self):
        # Find the schema directory
        dir = os.path.join(".")
        while SCHEMA_FOLDER not in os.listdir(dir):
            dir = os.path.join(dir, "..")

        self.path = os.path.abspath(CONFIG_PATH)
        FILEPATH_MANAGER.initialise(self.path, os.path.join(dir, SCHEMA_FOLDER))

    def test_config_root_dir_correct(self):
        self.assertEqual(self.path, FILEPATH_MANAGER.config_root_dir)

    def test_config_dir_correct(self):
        self.assertEqual(os.path.join(self.path, CONFIG_DIRECTORY), FILEPATH_MANAGER.config_dir)

    def test_component_dir_correct(self):
        self.assertEqual(os.path.join(self.path, COMPONENT_DIRECTORY), FILEPATH_MANAGER.component_dir)

    def test_synoptic_dir_correct(self):
        self.assertEqual(os.path.join(self.path, SYNOPTIC_DIRECTORY), FILEPATH_MANAGER.synoptic_dir)

    def test_config_folder_path_correct(self):
        config = "test"
        self.assertEqual(os.path.join(self.path, CONFIG_DIRECTORY, config) + os.sep,
                         FILEPATH_MANAGER.get_config_path(config))

    def test_component_folder_path_correct(self):
        component = "test"
        self.assertEqual(os.path.join(self.path, COMPONENT_DIRECTORY, component) + os.sep,
                         FILEPATH_MANAGER.get_component_path(component))

    def test_synoptic_file_path_correct(self):
        synoptic = "test"
        self.assertEqual(os.path.join(self.path, SYNOPTIC_DIRECTORY, synoptic) + ".xml",
                         FILEPATH_MANAGER.get_synoptic_path(synoptic))