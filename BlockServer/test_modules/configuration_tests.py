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

from BlockServer.config.configuration import Configuration

from BlockServer.mocks.mock_configuration import MockConfigurationFileManager
from BlockServer.mocks.mock_configuration import MockConfigurationXmlConverter
from BlockServer.mocks.mock_configuration import MockConfigurationJsonConverter
from BlockServer.core.macros import MACROS

# Args are : name, pv, group, local and visible
NEW_BLOCK_ARGS = {'name': "TESTBLOCK1", 'pv': "PV1", 'group': "GROUP1", 'local': True, 'visible': True}
NEW_BLOCK_ARGS_2 = {'name': "TESTBLOCK2", 'pv': "PV2", 'group': "GROUP2", 'local': True, 'visible': True}

# TODO write tests for ConfigurationFileManager (config/file_manager.py)


class TestConfigurationSequence(unittest.TestCase):
    def setUp(self):
        # Create a new configuration
        self.file_manager = MockConfigurationFileManager()
        self.json_converter = MockConfigurationJsonConverter()
        self.config = Configuration(MACROS)

    def tearDown(self):
        pass

    def test_new_config_has_blank_name(self):
        # assert
        self.assertEqual(self.config.get_name(), "")

    def test_adding_a_block_and_getting_block_names_returns_the_name_of_the_block(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        block_name = block_args['name']
        # act
        cf.add_block(**block_args)
        blocks = cf.blocks.keys()
        # assert
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0], block_name.lower())

    def test_adding_a_block_also_adds_its_associated_group(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        group_name = block_args['group']
        # act
        cf.add_block(**block_args)
        groups = cf.groups.keys()
        # assert
        self.assertEqual(len(groups), 1)
        self.assertTrue(group_name.lower() in groups)

    def test_adding_the_same_block_twice_raises_exception(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        # act
        cf.add_block(**block_args)
        # assert
        self.assertRaises(Exception, cf.add_block, *block_args)

    def test_adding_ioc_correctly_adds_to_ioc_list(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # act
        cf.add_ioc(ioc_name)
        iocs = cf.iocs
        # assert
        self.assertEqual(len(iocs), 1)
        self.assertEqual(iocs["TESTIOC"].name, ioc_name)

    def test_adding_the_same_ioc_twice_does_not_raise_exception(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # act
        cf.add_ioc(ioc_name)
        # assert
        try:
            cf.add_ioc(ioc_name)
        except:
            self.fail("Adding the same ioc twice raised Exception unexpectedly!")

    def test_get_blocks_names_returns_empty_list_when_no_blocks(self):
        # arrange
        cf = self.config
        # act
        block_names = cf.blocks.keys()
        # assert
        self.assertEqual(len(block_names), 0)


if __name__ == '__main__':
    #start blockserver
    unittest.main()
