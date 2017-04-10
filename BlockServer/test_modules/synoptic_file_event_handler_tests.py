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

from BlockServer.fileIO.schema_checker import NotConfigFileException
from BlockServer.fileIO.synoptic_file_event_handler import SynopticFileEventHandler
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from mock import MagicMock

TEST_DIRECTORY = os.path.abspath(os.path.join(__file__, "..", "test_configs"))
SCHEMA_DIR = os.path.abspath(os.path.join("..", "..", "schema"))
SAMPLE_SYNOPTIC = u"""<?xml version="1.0" ?>
<instrument xmlns="http://www.isis.stfc.ac.uk//instrument">
    <name>test1</name>
    <components>
        <component>
            <name>DF</name>
            <type>DANFYSIK</type>
            <target>
                <name>Danfysik</name>
                <type>OPI</type>
                <properties>
                    <property>
                        <key>DFKPS</key>
                        <value>DFKPS_01</value>
                    </property>
                </properties>
            </target>
            <pvs/>
            <components/>
        </component>
    </components>
</instrument>
"""


class TestConfigFileEventHandler(unittest.TestCase):
    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCHEMA_DIR)
        self.file_manager = MockConfigurationFileManager()
        self.synoptic_manager = MagicMock()
        self.eh = SynopticFileEventHandler(SCHEMA_DIR, RLock(), self.synoptic_manager)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_when_getting_name_from_path_correct_synoptic_name_is_returned(self):
        # Arrange
        synoptic_name = 'TEST_SYNOPTIC'
        synoptic_file = synoptic_name + '.xml'
        path = os.path.join(FILEPATH_MANAGER.synoptic_dir, synoptic_file)

        # Act
        name = self.eh._get_name(path)

        # Assert
        self.assertEqual(name, synoptic_name)

    def test_when_deleted_event_then_recover_called(self):
        # Arrange
        synoptic_name = 'TEST_SYNOPTIC'
        synoptic_file = synoptic_name + '.xml'
        path = os.path.join(FILEPATH_MANAGER.synoptic_dir, synoptic_file)

        # Act
        self.eh.on_deleted(DirDeletedEvent(path))

        # Assert
        self.synoptic_manager.recover_from_version_control.assert_called()

    def test_when_reading_valid_xml_data_then_is_successfully_returned_by_check_valid(self):
        # Arrange
        synoptic_name = 'TEST_SYNOPTIC'
        synoptic_file = synoptic_name + '.xml'
        path = os.path.join(FILEPATH_MANAGER.synoptic_dir, synoptic_file)

        # Act
        self.synoptic_manager.load_synoptic.return_value = SAMPLE_SYNOPTIC
        xml_data = self.eh._check_valid(path)

        # Assert
        self.assertEqual(xml_data, SAMPLE_SYNOPTIC)

    def test_given_invalid_extension_then_raise_not_config_file_exception(self):
        # Arrange
        synoptic_name = 'TEST_SYNOPTIC'
        synoptic_file = synoptic_name + '.txt'
        path = os.path.join(FILEPATH_MANAGER.synoptic_dir, synoptic_file)

        # Act
        self.synoptic_manager.load_synoptic.return_value = SAMPLE_SYNOPTIC

        # Assert
        with self.assertRaises(NotConfigFileException):
            self.eh._check_valid(path)

    def test_when_file_modified_event_then_reload_and_update(self):
        # Arrange
        synoptic_name = 'TEST_SYNOPTIC'
        synoptic_file = synoptic_name + '.xml'
        path = os.path.join(FILEPATH_MANAGER.synoptic_dir, synoptic_file)
        e = FileModifiedEvent(path)

        self.synoptic_manager.load_synoptic.return_value = SAMPLE_SYNOPTIC

        # Act
        self.eh.file_modified(e)

        # Assert
        self.synoptic_manager.load_synoptic.assert_called_with(path)
        self.synoptic_manager.update.assert_called_with(SAMPLE_SYNOPTIC)
