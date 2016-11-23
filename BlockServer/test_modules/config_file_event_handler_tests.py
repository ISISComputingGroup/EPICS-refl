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
from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.fileIO.config_file_event_handler import ConfigFileEventHandler
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from mock import MagicMock

TEST_DIRECTORY = os.path.abspath("test_configs")
SCHEMA_DIR = os.path.abspath(os.path.join("..", "..", "..", "..", "schema", "configurations"))


class TestConfigFileEventHandler(unittest.TestCase):
    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCHEMA_DIR)
        self.file_manager = MockConfigurationFileManager()
        self.config_list_manager = MagicMock()
        self.eh = ConfigFileEventHandler(SCHEMA_DIR, RLock(), self.config_list_manager, False)
        print TEST_DIRECTORY

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_get_config_name_valid_structure(self):
        config_folder = 'TEST_CONFIG'
        name = self.eh._get_name(os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml'))

        self.assertEqual(name, config_folder)

    def test_file_not_in_correct_place(self):
        self.assertFalse(self.eh._check_file_at_root(os.path.join(FILEPATH_MANAGER.config_root_dir, 'TEST_FILE.xml')))

    def test_when_initialised_as_component_then_saved_as_component(self):
        self.eh = ConfigFileEventHandler(SCHEMA_DIR, RLock(), self.config_list_manager, True)

        self.assertTrue(self.eh._is_comp)

    def test_when_deleted_event_then_recover_called(self):
        config_folder = 'TEST_CONFIG'
        path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml')

        self.eh.on_deleted(DirDeletedEvent(path))

        self.config_list_manager.recover.assert_called()

    def test_when_file_modified_event_then_updated(self):
        config_folder = 'TEST_CONFIG'
        path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml')
        name = self.eh._get_name(os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml'))
        e = FileModifiedEvent(path)

        self.eh.on_any_event(e)

        self.config_list_manager.update.assert_called()

    def test_when_file_moved_event_then_deleted_old(self):
        config_folder_src = 'TEST_CONFIG'
        config_folder_dest = "TEST_CONFIG2"
        src_path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder_src, 'TEST_FILE.xml')
        dest_path = os.path.join(FILEPATH_MANAGER.config_dir, config_folder_dest, 'TEST_FILE.xml')
        e = FileMovedEvent(src_path, dest_path)

        self.eh.on_any_event(e)

        self.config_list_manager.update.assert_called()
