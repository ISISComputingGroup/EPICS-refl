import unittest
import json
from collections import OrderedDict

from BlockServer.config.containers import Group, Block, IOC
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
        groups["TESTGROUP3".lower()] = Group("TESTGROUP3", "TESTSUBCONFIG1")
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
        self.assertIsNone(returned[0]["subconfig"])
        self.assertIsNone(returned[1]["subconfig"])
        self.assertEqual(returned[2]["subconfig"], "TESTSUBCONFIG1")
        self.assertIsNone(returned[3]["subconfig"])





