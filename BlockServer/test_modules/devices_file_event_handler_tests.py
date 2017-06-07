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

from BlockServer.fileIO.devices_file_event_handler import DevicesFileEventHandler
from BlockServer.fileIO.schema_checker import NotConfigFileException
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from mock import MagicMock

TEST_DIRECTORY = os.path.abspath(os.path.join(__file__, "..", "test_configs"))
SCHEMA_DIR = os.path.abspath(os.path.join("..", "..", "schema"))
DEVICES_FILE = "screens.xml"
VALID_DEVICES_DATA = u"""<?xml version="1.0" ?>
<devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
    <device>
        <name>TEST_DEVICE</name>
        <key>Eurotherm</key>
        <type>OPI</type>
        <properties/>
    </device>
</devices>
"""


class TestConfigFileEventHandler(unittest.TestCase):
    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCHEMA_DIR)
        self.file_manager = MockConfigurationFileManager()
        self.devices_manager = MagicMock()
        self.eh = DevicesFileEventHandler(SCHEMA_DIR, RLock(), self.devices_manager)
        self.path = os.path.join(FILEPATH_MANAGER.devices_dir, DEVICES_FILE)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_when_deleted_event_then_recover_called(self):

        # Act
        self.eh.on_deleted(DirDeletedEvent(self.path))

        # Assert
        self.devices_manager.recover_from_version_control.assert_called()

    def test_when_reading_valid_xml_data_then_is_successfully_returned_by_check_valid(self):

        # Act
        self.devices_manager.load_devices.return_value = VALID_DEVICES_DATA
        xml_data = self.eh._check_valid(self.path)

        # Assert
        self.assertEqual(xml_data, VALID_DEVICES_DATA)

    def test_given_invalid_extension_then_raise_not_config_file_exception(self):
        # Act
        self.path += ".txt"
        self.devices_manager.load_synoptic.return_value = VALID_DEVICES_DATA

        # Assert
        with self.assertRaises(NotConfigFileException):
            self.eh._check_valid(self.path)

    def test_when_file_modified_event_then_reload_and_update(self):
        # Arrange
        e = FileModifiedEvent(self.path)

        self.devices_manager.load_devices.return_value = VALID_DEVICES_DATA

        # Act
        self.eh.file_modified(e)

        # Assert
        self.devices_manager.load_devices.assert_called_with(self.path)
        self.devices_manager.update.assert_called_with(VALID_DEVICES_DATA)
