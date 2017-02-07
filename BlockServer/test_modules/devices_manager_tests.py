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

from server_common.utilities import compress_and_hex, dehex_and_decompress
from BlockServer.devices.devices_manager import DevicesManager, GET_SCREENS
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.mocks.mock_version_control import *
from ConfigVersionControl.version_control_exceptions import *

CONFIG_PATH = os.path.join(os.getcwd(), "test_configs")
BASE_PATH = "example_base"
SCREENS_FILE = "screens.xml"
SCHEMA_FOLDER = "schema"

EXAMPLE_DEVICES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
    <device>
        <name>Eurotherm 1</name>
        <key>Eurotherm</key>
        <type>OPI</type>
        <properties>
            <property>
                <key>EURO</key>
                <value>EUROTHERM1</value>
            </property>
        </properties>
    </device>
</devices>"""

EXAMPLE_DEVICES_2 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
    <device>
        <name>Eurotherm 2</name>
        <key>Eurotherm</key>
        <type>OPI</type>
        <properties>
            <property>
                <key>EURO</key>
                <value>EUROTHERM1</value>
            </property>
        </properties>
    </device>
</devices>"""

INVALID_DEVICES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
    <device>
        <name>Eurotherm 1</name>
        <key>Eurotherm</key>
        <type>NOT A CORRECT TYPE</type>
        <properties>
            <property>
                <key>EURO</key>
                <value>EUROTHERM1</value>
            </property>
        </properties>
    </device>
</devices>"""

SCHEMA_PATH = os.path.abspath(os.path.join(".", "..","schema"))


def get_expected_devices_file_path():
    return os.path.join(FILEPATH_MANAGER.devices_dir, SCREENS_FILE)


class MockDevicesFileIO(object):
    def __init__(self):
        self.files = dict()

    def load_devices_file(self, file_name):
        if file_name not in self.files:
            raise IOError("File not found")

        return self.files[file_name]

    def save_devices_file(self, file_name, data):
        self.files[file_name] = data


class TestDevicesManagerSequence(unittest.TestCase):
    def setUp(self):
        # Make directory and fill with fake content
        FILEPATH_MANAGER.initialise(os.path.abspath(CONFIG_PATH), os.path.abspath(SCHEMA_PATH))

        # Find the schema directory
        dir = os.path.join(".")
        while SCHEMA_FOLDER not in os.listdir(dir):
            dir = os.path.join(dir, "..")

        self.dir = os.path.join(dir, SCHEMA_FOLDER)

        self.bs = MockBlockServer()
        self.file_io = MockDevicesFileIO()
        self.dm = DevicesManager(self.bs, self.dir, MockVersionControl(), self.file_io)

    def tearDown(self):
        pass

    def test_get_devices_filename_returns_correct_file_name(self):
        # Arrange
        expected = get_expected_devices_file_path()

        # Act
        result = self.dm.get_devices_filename()

        # Assert
        self.assertEquals(expected, result)

    def test_when_devices_screens_file_does_not_exist_then_current_uses_blank_devices_data(self):
        # Arrange
        self.dm.initialise()

        # Assert
        self.assertTrue(len(self.file_io.files) == 0)
        self.assertEquals(self.bs.pvs[GET_SCREENS], compress_and_hex(self.dm.get_blank_devices()))

    def test_given_invalid_devices_data_when_device_xml_saved_then_not_saved(self):
        # Arrange:
        self.dm.initialise()

        # Act: Save invalid new data to file
        self.dm.save_devices_xml(INVALID_DEVICES)

        # Assert
        # Should stay as blank (i.e. the previous value)
        self.assertEquals(self.dm.get_blank_devices(), dehex_and_decompress(self.bs.pvs[GET_SCREENS]))

    def test_given_valid_devices_data_when_device_xml_saved_then_saved(self):
        # Arrange:
        self.dm.initialise()

        # Act: Save the new data to file
        self.dm.save_devices_xml(EXAMPLE_DEVICES)

        # Assert:
        # Device screens in blockserver should have been updated with value written to device manager
        self.assertEquals(EXAMPLE_DEVICES, dehex_and_decompress(self.bs.pvs[GET_SCREENS]))

    def test_on_update_cannot_add_to_version_control_does_not_raise_specified_exception(self):
        # Arrange
        dm = DevicesManager(self.bs, self.dir, FailOnAddMockVersionControl(), self.file_io)
        dm.initialise()

        # Act and assert
        try:
            dm.update(EXAMPLE_DEVICES)
        except AddToVersionControlException as err:
            self.fail("Oops add raised")

    def test_on_update_cannot_commit_to_version_control_does_not_raise_specified_exception(self):
        # Arrange
        dm = DevicesManager(self.bs, self.dir, FailOnCommitMockVersionControl(), self.file_io)
        dm.initialise()

        # Act and assert
        try:
            dm.update(EXAMPLE_DEVICES, "Some commit message")
        except CommitToVersionControlException as err:
            self.fail("Oops add raised")

    def test_on_recover_from_version_control_does_not_raise_specified_exception(self):
        # Arrange
        dm = DevicesManager(self.bs, self.dir, FailOnUpdateMockVersionControl(), self.file_io)
        dm.initialise()

        # Act and assert
        try:
            dm.recover_from_version_control()
        except UpdateFromVersionControlException as err:
            self.fail("Oops update raised")