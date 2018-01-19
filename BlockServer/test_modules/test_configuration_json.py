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
import json
from collections import OrderedDict

from BlockServer.config.group import Group
from BlockServer.config.block import Block
from BlockServer.config.ioc import IOC
from BlockServer.config.json_converter import ConfigurationJsonConverter
from BlockServer.core.constants import GRP_NONE

GROUPS_JSON = \
    '[{"name":"TESTGROUP1","blocks":["TESTBLOCK1","TESTBLOCK2"]},' \
    '{"name":"TESTGROUP2","blocks":["TESTBLOCK3","TESTBLOCK4"]}]'


class TestConfigurationJsonConverterSequence(unittest.TestCase):
    def setUp(self):
        # Create a new XML converter
        self.json_converter = ConfigurationJsonConverter()

    def tearDown(self):
        pass

    def test_groups_to_json_converts_correctly(self):
        # Arrange
        jc = self.json_converter
        groups = OrderedDict()
        groups["TESTGROUP1".lower()] = Group("TESTGROUP1")
        groups["TESTGROUP1".lower()].blocks = ["TESTGROUP1BLOCK1", "TESTGROUP1BLOCK2"]
        groups["TESTGROUP2".lower()] = Group("TESTGROUP2")
        groups["TESTGROUP2".lower()].blocks = ["TESTGROUP2BLOCK1", "TESTGROUP2BLOCK2"]
        groups["TESTGROUP3".lower()] = Group("TESTGROUP3", "TESTCOMPONENT1")
        groups["TESTGROUP3".lower()].blocks = ["TESTGROUP3BLOCK1", "TESTGROUP3BLOCK2"]
        groups[GRP_NONE.lower()] = Group(GRP_NONE)
        groups[GRP_NONE.lower()].blocks = ["TESTGROUPNONEBLOCK1", "TESTGROUPNONEBLOCK2"]

        # act
        groups_json = jc.groups_to_json(groups)
        returned = json.loads(groups_json)
        # Returned should be a list of dictionaries

        # Assert
        self.assertEqual(len(returned), 4)
        self.assertEqual(returned[0]['name'], "TESTGROUP1")
        self.assertEqual(returned[1]['name'], "TESTGROUP2")
        self.assertEqual(returned[2]['name'], "TESTGROUP3")
        self.assertEqual(returned[3]['name'], GRP_NONE)
        self.assertTrue("TESTGROUP1BLOCK1" in returned[0]['blocks'])
        self.assertTrue("TESTGROUP1BLOCK2" in returned[0]['blocks'])
        self.assertTrue("TESTGROUP2BLOCK1" in returned[1]['blocks'])
        self.assertTrue("TESTGROUP2BLOCK2" in returned[1]['blocks'])
        self.assertTrue("TESTGROUP3BLOCK1" in returned[2]['blocks'])
        self.assertTrue("TESTGROUP3BLOCK2" in returned[2]['blocks'])
        self.assertTrue("TESTGROUPNONEBLOCK1" in returned[3]['blocks'])
        self.assertTrue("TESTGROUPNONEBLOCK2" in returned[3]['blocks'])
        self.assertIsNone(returned[0]["component"])
        self.assertIsNone(returned[1]["component"])
        self.assertEqual(returned[2]["component"], "TESTCOMPONENT1")
        self.assertIsNone(returned[3]["component"])





