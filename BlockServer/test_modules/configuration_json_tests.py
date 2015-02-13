import unittest
import json
from collections import OrderedDict

from config.containers import Group, Block, IOC
from config.json_converter import ConfigurationJsonConverter
from config.constants import GRP_NONE

GROUPS_JSON = \
    '[{"name":"TESTGROUP1","blocks":["TESTBLOCK1","TESTBLOCK2"]},' \
    '{"name":"TESTGROUP2","blocks":["TESTBLOCK3","TESTBLOCK4"]}]'


class TestConfigurationJsonConverterSequence(unittest.TestCase):
    def setUp(self):
        # Create a new XML converter
        self.json_converter = ConfigurationJsonConverter()

    def tearDown(self):
        pass

    def test_json_to_groups_converts_correctly(self):
        # arrange
        jc = self.json_converter

        # act
        ans = jc.groups_from_json(GROUPS_JSON)

        # assert
        self.assertEqual(len(ans), 2)
        names = [x['name'] for x in ans]
        self.assertTrue("TESTGROUP1" in names)
        self.assertTrue("TESTGROUP2" in names)
        blocks1 = [x for g in ans for x in g['blocks'] if g['name'] == "TESTGROUP1"]
        self.assertTrue("TESTBLOCK1" in blocks1)
        self.assertTrue("TESTBLOCK2" in blocks1)
        blocks2 = [x for g in ans for x in g['blocks'] if g['name'] == "TESTGROUP2"]
        self.assertTrue("TESTBLOCK3" in blocks2)
        self.assertTrue("TESTBLOCK4" in blocks2)

    def test_groups_to_json_converts_correctly(self):
        # arrange
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
        #returned should be a list of dictionaries

        # assert
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

    def test_config_to_json_converts_correctly(self):
        # arrange
        jc = self.json_converter

        #Blocks
        blocks = OrderedDict()
        blocks["TESTGROUP1BLOCK1".lower()] = Block("TESTGROUP1BLOCK1", "PV1")
        blocks["TESTGROUP1BLOCK2".lower()] = Block("TESTGROUP1BLOCK2", "PV2")
        #Groups
        groups = OrderedDict()
        groups["TESTGROUP1".lower()] = Group("TESTGROUP1")
        groups["TESTGROUP1".lower()].blocks = ["TESTGROUP1BLOCK1", "TESTGROUP1BLOCK2"]
        groups[GRP_NONE.lower()] = Group(GRP_NONE)
        #IOCs
        iocs = OrderedDict()
        iocs["SIMPLE1"] = IOC("SIMPLE1")
        iocs["SIMPLE2"] = IOC("SIMPLE2")

        # act
        js = jc.config_to_json("", blocks, groups, iocs, None)
        conf = json.loads(js)

        # assert
        self.assertEqual(len(conf['iocs']), 2)
        iocs = [x['name'] for x in conf['iocs']]
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        self.assertEqual(len(conf['blocks']), 2)
        blocks = [x for x in conf['blocks'].keys()]
        self.assertTrue("TESTGROUP1BLOCK1" in blocks)
        self.assertTrue("TESTGROUP1BLOCK2" in blocks)
        self.assertEqual(len(conf['groups']), 2)
        groups = [x['name'] for x in conf['groups']]
        self.assertTrue("TESTGROUP1" in groups)
        self.assertTrue(GRP_NONE in groups)
        self.assertEqual(len(conf['components']), 0)

    def test_config_to_json_empty_config_converts_correctly(self):
        # arrange
        jc = self.json_converter

        # act
        js = jc.config_to_json("", None, None, None, None)
        conf = json.loads(js)

        # assert
        self.assertEqual(len(conf['iocs']), 0)
        self.assertEqual(len(conf['blocks']), 0)
        self.assertEqual(len(conf['groups']), 0)
        self.assertEqual(len(conf['components']), 0)



