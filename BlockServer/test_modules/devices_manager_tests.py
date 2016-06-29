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
import shutil

from server_common.utilities import compress_and_hex
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.core.devices_manager import DevicesManager
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.core.pv_names import BlockserverPVNames
from xml.dom import minidom


CONFIG_PATH = os.path.join(os.getcwd(),"test_configs")
BASE_PATH = "example_base"
SCREENS_FILE = "screens.xml"

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
    return os.path.join(FILEPATH_MANAGER.get_config_path(BASE_PATH),SCREENS_FILE)


class TestDevicesManagerSequence(unittest.TestCase):
    def setUp(self):
        # Make directory and fill with fake content
        FILEPATH_MANAGER.initialise(os.path.abspath(CONFIG_PATH))

        test_config_path = FILEPATH_MANAGER.get_config_path(BASE_PATH)
        if os.path.exists(test_config_path):
            shutil.rmtree(test_config_path)
        shutil.copytree(os.path.join(os.getcwd(),BASE_PATH), test_config_path)

        self.cas = MockCAServer()
        self.dm = DevicesManager(MockBlockServer(), self.cas, SCHEMA_PATH, MockVersionControl())

    def tearDown(self):
        # Delete any configs created as part of the test
        path = FILEPATH_MANAGER.config_root_dir
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_get_devices_filename_raises_IOError_when_no_current_config_file_set(self):
        # Arrange
        # Act
        # Assert
        with self.assertRaises(IOError):
            self.dm.get_devices_filename()

    def test_when_set_config_file_does_not_exist_then_get_devices_filename_raises_IOError(self):
        # Arrange
        non_existing_path = os.path.join("Non", "existing")
        self.dm.set_current_config_name(non_existing_path)

        # Act
        # Assert
        with self.assertRaises(IOError):
            self.dm.get_devices_filename()

    def test_when_config_file_is_set_then_get_devices_filename_returns_correct_file_name(self):
        # Arrange
        self.dm.set_current_config_name(BASE_PATH)
        expected = get_expected_devices_file_path()

        # Act
        result = self.dm.get_devices_filename()

        # Assert
        self.assertEquals(expected, result)

    def test_when_config_file_does_not_exist_then_load_current_uses_blank_devices_data(self):
        #Arrange
        self.dm.set_current_config_name("DOES_NOT_EXIST")
        pv_key = BlockserverPVNames.GET_SCREENS

        #Act
        self.dm.load_current()

        #Assert
        self.assertEquals(self.dm._cas.pv_list[pv_key],compress_and_hex(self.dm.get_blank_devices()))


    def test_loading_config_file_creates_a_pv_in_the_ca_server_with_correct_key(self):
        # Arrange
        self.dm.set_current_config_name(BASE_PATH)
        expected_key = BlockserverPVNames.GET_SCREENS
        self.assertFalse(self.cas.pv_list.has_key(expected_key))

        # Act
        self.dm.load_current()

        # Assert
        self.assertTrue(self.cas.pv_list.has_key(expected_key))

    def test_loading_config_file_creates_a_pv_in_the_ca_server_with_correct_data(self):
        # Arrange
        self.dm.set_current_config_name(BASE_PATH)
        pv_key = BlockserverPVNames.GET_SCREENS

        devices_file_name = get_expected_devices_file_path()
        with open(devices_file_name, 'r') as devfile:
            data = devfile.read()

        expected_data = compress_and_hex(data)

        # Act
        self.dm.load_current()

        # Assert
        self.assertEquals(expected_data, self.cas.pv_list[pv_key])

    def test_given_invalid_devices_data_when_device_xml_saved_then_error(self):
        self.dm.set_current_config_name(BASE_PATH)
        devices_file_name = get_expected_devices_file_path()

        # Act: Save the new data to file
        with self.assertRaises(Exception):
            self.dm.save_devices_xml(INVALID_DEVICES)

    def test_given_new_xml_data_when_device_xml_saved_then_screens_file_contains_prettified_new_data(self):
        self.dm.set_current_config_name(BASE_PATH)
        devices_file_name = get_expected_devices_file_path()

        # New data
        new_data = EXAMPLE_DEVICES

        # Act: Save the new data to file
        self.dm.save_devices_xml(new_data)

        expected_data = minidom.parseString(new_data).toprettyxml()
        with open(devices_file_name, 'r') as devfile:
            result_data = devfile.read()

        # Assert
        self.assertEquals(expected_data,result_data)

    def test_save_devices_xml_creates_get_screens_pv(self):
        self.dm.set_current_config_name(BASE_PATH)
        devices_file_name = get_expected_devices_file_path()
        expected_key = BlockserverPVNames.GET_SCREENS

        # Act: Save the new data to file
        self.dm.save_devices_xml(EXAMPLE_DEVICES)

        # Assert
        self.assertTrue(self.cas.pv_list.has_key(expected_key))

    def test_save_devices_xml_creates_pv_with_prettified_input_data(self):
        self.dm.set_current_config_name(BASE_PATH)
        devices_file_name = get_expected_devices_file_path()

        # Arrange
        new_xml_data = EXAMPLE_DEVICES_2

        # Act: Save the new data to file
        self.dm.save_devices_xml(new_xml_data)
        expected_data = minidom.parseString(new_xml_data).toprettyxml()
        with open(devices_file_name, 'r') as devfile:
            result_data = devfile.read()

        # Assert
        self.assertEquals(expected_data,result_data)
