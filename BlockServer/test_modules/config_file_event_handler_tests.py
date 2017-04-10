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

from threading import RLock
import unittest
import os
import shutil

from watchdog.events import *
from BlockServer.fileIO.config_file_event_handler import ConfigFileEventHandler
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from mock import MagicMock

TEST_DIRECTORY = os.path.abspath(os.path.join(__file__, "..", "test_configs"))
SCHEMA_DIR = os.path.abspath(os.path.join("..", "..", "schema", "configurations"))


class TestConfigFileEventHandler(unittest.TestCase):
    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCHEMA_DIR)
        self.file_manager = MockConfigurationFileManager()
        self.config_list_manager = MagicMock()
        self.is_component = False
        self.eh = ConfigFileEventHandler(RLock(), self.config_list_manager, self.is_component)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_when_getting_name_from_path_correct_config_name_is_returned(self):
        # Arrange
        config_folder = 'TEST_CONFIG'
        path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml')

        # Act
        name = self.eh._get_name(path)

        # Assert
        self.assertEqual(name, config_folder)

    def test_file_not_in_correct_place(self):
        # Arrange
        path = os.path.join(FILEPATH_MANAGER.config_root_dir, 'TEST_FILE.xml')

        # Assert
        self.assertFalse(self.eh._check_file_at_root(path))

    def test_when_initialised_as_component_then_saved_as_component(self):
        # Arrange
        self.is_component = True

        # Act
        self.eh = ConfigFileEventHandler(RLock(), self.config_list_manager, self.is_component)

        # Assert
        self.assertTrue(self.eh._is_comp)

    def test_when_deleted_event_then_recover_called(self):
        # Arrange
        config_folder = 'TEST_CONFIG'
        path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml')

        # Act
        self.eh.on_deleted(DirDeletedEvent(path))

        # Assert
        self.config_list_manager.recover_from_version_control.assert_called()

    def test_when_file_modified_event_then_reload_and_update(self):
        # Arrange
        config_folder = 'TEST_CONFIG'
        path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml')
        e = FileModifiedEvent(path)

        active_config = MagicMock()
        self.config_list_manager.load_config.return_value = active_config

        # Act
        self.eh.file_modified(e)

        # Assert
        self.config_list_manager.load_config.assert_called_with(config_folder, self.is_component)
        self.config_list_manager.update.assert_called_with(active_config, self.is_component)
