import unittest
import os
import shutil
import datetime

from BlockServer.core.inactive_config_holder import ConfigHolder
from BlockServer.config.configuration import Configuration
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_version_control import MockVersionControl


CONFIG_PATH = "./test_configs/"
BASE_PATH = "./example_base/"

# Helper functions
def add_block(ch, name, pv, group, local=True):
    data = {'name': name, 'pv': pv, 'group': group, 'local': local}
    ch.add_block(data)

def create_dummy_config():
    config = Configuration(MACROS)
    config.add_block("TESTBLOCK1", "PV1", "GROUP1", True)
    config.add_block("TESTBLOCK2", "PV2", "GROUP2", True)
    config.add_block("TESTBLOCK3", "PV3", "GROUP2", True)
    config.add_block("TESTBLOCK4", "PV4", "NONE", False)
    config.add_ioc("SIMPLE1")
    config.add_ioc("SIMPLE2")
    config.set_name("DUMMY")
    return config


def create_dummy_subconfig():
    config = Configuration(MACROS)
    config.add_block("SUBBLOCK1", "PV1", "GROUP1", True)
    config.add_block("SUBBLOCK2", "PV2", "SUBGROUP", True)
    config.add_ioc("SUBSIMPLE1")
    return config


class TestConfigHolderSequence(unittest.TestCase):
    def setUp(self):
        # Create components folder and copying DEFAULT_COMPONENT fileIO into it
        path = os.path.abspath(CONFIG_PATH)
        os.mkdir(path)
        component_path = path + "/components/"
        os.mkdir(component_path)
        shutil.copytree(BASE_PATH, component_path + "/" + DEFAULT_COMPONENT)

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(CONFIG_PATH)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_dummy_name(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        self.assertEqual(ch.get_config_name(), "DUMMY")

    def test_getting_blocks_json_with_no_blocks_returns_empty_list(self):
        # arrange
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=None)
        # act
        blocks = ch.get_blocknames()
        # assert
        self.assertEqual(len(blocks), 0)

    def test_dummy_config_blocks(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 4)
        self.assertEqual(blks[0], "TESTBLOCK1")
        self.assertEqual(blks[1], "TESTBLOCK2")
        self.assertEqual(blks[2], "TESTBLOCK3")
        self.assertEqual(blks[3], "TESTBLOCK4")

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 4)
        self.assertTrue("TESTBLOCK1".lower() in blk_details)
        self.assertTrue("TESTBLOCK2".lower() in blk_details)
        self.assertTrue("TESTBLOCK3".lower() in blk_details)
        self.assertTrue("TESTBLOCK4".lower() in blk_details)
        self.assertEqual(blk_details["TESTBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["TESTBLOCK2".lower()].pv, "PV2")
        self.assertEqual(blk_details["TESTBLOCK3".lower()].pv, "PV3")
        self.assertEqual(blk_details["TESTBLOCK4".lower()].pv, "PV4")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK2".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK3".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK4".lower()].local, False)

    def test_dummy_config_blocks_add_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 6)
        self.assertEqual(blks[4], "SUBBLOCK1")
        self.assertEqual(blks[5], "SUBBLOCK2")

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 6)
        self.assertTrue("SUBBLOCK1".lower() in blk_details)
        self.assertTrue("SUBBLOCK2".lower() in blk_details)
        self.assertEqual(blk_details["SUBBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["SUBBLOCK2".lower()].pv, "PV2")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)

    def test_dummy_config_blocks_add_remove_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        ch.remove_subconfig("TESTSUBCONFIG")

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 4)
        self.assertFalse("SUBBLOCK1" in blks)
        self.assertFalse("SUBBLOCK2" in blks)

    def test_dummy_config_groups(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 3)
        self.assertTrue("GROUP1".lower() in grp_details)
        self.assertTrue("GROUP2".lower() in grp_details)
        self.assertTrue("NONE".lower() in grp_details)
        self.assertTrue("TESTBLOCK1" in grp_details["GROUP1".lower()].blocks)
        self.assertTrue("TESTBLOCK2" in grp_details["GROUP2".lower()].blocks)
        self.assertTrue("TESTBLOCK3" in grp_details["GROUP2".lower()].blocks)
        self.assertTrue("TESTBLOCK4" in grp_details["NONE".lower()].blocks)

    def test_dummy_config_groups_add_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 4)
        self.assertTrue("SUBGROUP".lower() in grp_details)
        self.assertTrue("SUBBLOCK1" in grp_details["GROUP1".lower()].blocks)
        self.assertTrue("SUBBLOCK2" in grp_details["SUBGROUP".lower()].blocks)

    def test_dummy_config_groups_add_remove_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)
        ch.remove_subconfig("TESTSUBCONFIG")

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 3)
        self.assertFalse("SUBGROUP".lower() in grp_details)
        self.assertFalse("SUBBLOCK1" in grp_details["GROUP1".lower()].blocks)

    def test_dummy_config_iocs(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 2)
        self.assertTrue("SIMPLE1" in ioc_names)
        self.assertTrue("SIMPLE2" in ioc_names)

    def test_dummy_config_iocs_add_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 3)
        self.assertTrue("SUBSIMPLE1" in ioc_names)

    def test_dummy_config_iocs_add_remove_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)
        ch.remove_subconfig("TESTSUBCONFIG")

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 2)
        self.assertFalse("SUBSIMPLE1" in ioc_names)

    def test_dummy_config_components(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        subs = ch.get_component_names()
        self.assertEqual(len(subs), 0)

    def test_dummy_config_components_add_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        subs = ch.get_component_names()
        self.assertEqual(len(subs), 1)
        self.assertTrue("TESTSUBCONFIG".lower() in subs)

    def test_dummy_config_components_add_remove_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)
        ch.remove_subconfig("TESTSUBCONFIG")

        subs = ch.get_component_names()
        self.assertEqual(len(subs), 0)
        self.assertFalse("TESTSUBCONFIG".lower() in subs)

    def test_add_block(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))

        blk = {"name": "TESTBLOCK1", "pv": "PV1", "local": True, "group": "NONE"}
        ch.add_block(blk)

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 1)
        self.assertTrue("TESTBLOCK1".lower() in blk_details)
        self.assertEqual(blk_details["TESTBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)

    def test_add_ioc(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))

        ch._add_ioc("TESTIOC1")

        ioc_details = ch.get_ioc_names()
        self.assertEqual(len(ioc_details), 1)
        self.assertTrue("TESTIOC1" in ioc_details)

    def test_add_ioc_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))

        ch.add_subconfig("TESTSUBCONFIG", Configuration(MACROS))
        ch._add_ioc("TESTIOC1", "TESTSUBCONFIG")

        ioc_details = ch.get_ioc_names()
        self.assertEqual(len(ioc_details), 1)
        self.assertTrue("TESTIOC1" in ioc_details)

    def test_get_config_details_empty(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))
        details = ch.get_config_details()

        self.assertEqual(len(details['blocks']), 0)
        self.assertEqual(len(details['groups']), 0)
        self.assertEqual(len(details['iocs']), 0)
        self.assertEqual(len(details['components']), 0)
        self.assertEqual(details['name'], "")
        self.assertEqual(details['description'], "")

    def test_get_config_details(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        details = ch.get_config_details()

        self.assertEqual(details["name"], "DUMMY")
        self.assertEqual(len(details['blocks']), 4)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertTrue("TESTBLOCK2" in blks)
        self.assertTrue("TESTBLOCK3" in blks)
        self.assertTrue("TESTBLOCK4" in blks)
        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["TESTBLOCK2", "TESTBLOCK3"])
        self.assertEqual(details['groups'][2]['blocks'], ["TESTBLOCK4"])
        self.assertEqual(len(details['iocs']), 2)
        iocs = [x['name'] for x in details['iocs']]
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        self.assertEqual(len(details['components']), 0)

    def test_get_config_details_add_subconfig(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))

        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        details = ch.get_config_details()
        self.assertEqual(len(details['blocks']), 2)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("SUBBLOCK1" in blks)
        self.assertTrue("SUBBLOCK2" in blks)
        self.assertEqual(len(details['groups']), 2)
        self.assertEqual(details['groups'][0]['blocks'], ["SUBBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["SUBBLOCK2"])
        self.assertEqual(len(details['iocs']), 1)
        iocs = [x['name'] for x in details['iocs']]
        self.assertTrue("SUBSIMPLE1" in iocs)
        self.assertEqual(len(details['components']), 1)

    def test_empty_config_save_and_load(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        self.assertEqual(ch.get_config_name(), "TESTCONFIG")
        self.assertEqual(len(ch.get_blocknames()), 0)
        self.assertEqual(len(ch.get_group_details()), 1)
        self.assertEqual(ch.get_group_details().keys()[0], "NONE".lower())
        self.assertEqual(len(ch.get_ioc_names()), 0)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_empty_subconfig_save_and_load(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))
        ch.save_configuration("TESTSUBCONFIG", True)
        ch.clear_config()

        conf = ch.load_configuration("TESTSUBCONFIG", True)
        ch.set_config(conf, True)

        self.assertEqual(ch.get_config_name(), "TESTSUBCONFIG")
        self.assertEqual(len(ch.get_blocknames()), 0)
        self.assertEqual(len(ch.get_group_details()), 1)
        self.assertEqual(ch.get_group_details().keys()[0], "NONE".lower())
        self.assertEqual(len(ch.get_ioc_names()), 0)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_dummy_config_save_and_load(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        self.assertEqual(ch.get_config_name(), "TESTCONFIG")
        self.assertEqual(len(ch.get_blocknames()), 4)
        self.assertEqual(len(ch.get_group_details()), 3)
        self.assertEqual(len(ch.get_ioc_names()), 2)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_save_comp_add_to_config(self):
        # Create and save a subconfig
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_subconfig())
        ch.save_configuration("TESTSUBCONFIG", True)
        ch.clear_config()

        # Create and save a config that uses the subconfig
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        comp = ch.load_configuration("TESTSUBCONFIG", True)
        ch.add_subconfig("TESTSUBCONFIG", comp)
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()
        conf = ch.load_configuration("TESTCONFIG", False)
        ch.set_config(conf)

        self.assertEqual(len(ch.get_component_names()), 1)

    def test_get_groups_list_from_empty_repo(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl())
        grps = ch.get_group_details()
        self.assertEqual(len(grps), 0)

    def test_add_config_and_get_groups_list(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 3)
        self.assertTrue('group1' in grps)
        self.assertTrue('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['none'].blocks)

    def test_add_subconfig_then_get_groups_list(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 4)
        self.assertTrue('subgroup' in grps)
        self.assertTrue("SUBBLOCK1" in grps['group1'].blocks)
        self.assertTrue("SUBBLOCK2" in grps['subgroup'].blocks)

    def test_add_subconfig_remove_subconfig_then_get_groups_list(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)
        ch.remove_subconfig("TESTSUBCONFIG")

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 3)
        self.assertFalse('subgroup' in grps)
        self.assertFalse("SUBBLOCK1" in grps['group1'].blocks)

    def test_redefine_groups_from_list_simple_move(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        # Move TESTBLOCK2 and TESTBLOCK4 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK4"]},
                 {"name": "group2", "blocks": ["TESTBLOCK3"]}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 3)
        self.assertTrue('group1' in grps)
        self.assertTrue('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)

    def test_redefine_groups_from_list_leave_group_empty(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        # Move TESTBLOCK2, TESTBLOCK3 and TESTBLOCK4 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK3", "TESTBLOCK4"]},
                 {"name": "group2", "blocks": []}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 2)  # The group1 and none
        self.assertTrue('group1' in grps)
        self.assertFalse('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)
        self.assertEqual(len(grps['none'].blocks), 0)

    def test_redefine_groups_from_list_subconfig_changes(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        sub = create_dummy_subconfig()
        ch.add_subconfig("TESTSUBCONFIG", sub)

        # Move SUBBLOCK1 and SUBBLOCK2 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK3", "TESTBLOCK4", "SUBBLOCK1",
                                               "SUBBLOCK2"]},
                 {"name": "group2", "blocks": []},
                 {"name": "subgroup", "blocks": []}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 2)  # group1 and none
        self.assertTrue('group1' in grps)
        self.assertFalse('group2' in grps)
        self.assertFalse('subgroup' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)
        self.assertEqual(len(grps['none'].blocks), 0)

    def test_set_config_details(self):
        # Need subconfig
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))
        ch.save_configuration("TESTSUBCONFIG", True)

        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "subconfig": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "subconfig": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "subconfig": None,
                             "visible": True}],
                       "components": [{"name": "TESTSUBCONFIG"}],
                       "groups":
                           [{"blocks": ["TESTBLOCK1"], "name": "Group1", "subconfig": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "subconfig": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "subconfig": None}],
                       "name": "TESTCONFIG",
                       "description": "Test Description"
                       }
        ch.set_config_details(new_details)
        details = ch.get_config_details()
        iocs = [x['name'] for x in details['iocs']]
        self.assertEqual(len(iocs), 2)
        self.assertTrue("TESTSIMPLE1" in iocs)
        self.assertTrue("TESTSIMPLE2" in iocs)

        self.assertEqual(len(details['blocks']), 3)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertTrue("TESTBLOCK2" in blks)
        self.assertTrue("TESTBLOCK3" in blks)

        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["TESTBLOCK2"])
        self.assertEqual(details['groups'][2]['blocks'], ["TESTBLOCK3"])

        self.assertEqual(len(details['components']), 1)
        self.assertEqual(details['components'][0]['name'], "TESTSUBCONFIG")

        self.assertEqual(details['name'], "TESTCONFIG")
        self.assertEqual(details['description'], "Test Description")

    def test_set_config_details_nonexistant_block_in_group_is_removed(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "subconfig": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "subconfig": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "subconfig": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "IDONTEXIST"], "name": "Group1", "subconfig": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "subconfig": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "subconfig": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['blocks']), 3)
        blks = [x['name'] for x in details['blocks']]
        self.assertFalse("IDONTEXIST" in blks)

        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])

        # Also check via get_group_details
        grp = ch.get_group_details()['group1']
        self.assertFalse("IDONTEXIST" in grp.blocks)

    def test_set_config_details_empty_group_is_removed(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": {}, "pvs": {},
                             "pvsets": {}, "subconfig": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": {}, "pvs": {},
                             "pvsets": {}, "subconfig": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "subconfig": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "TESTBLOCK2"], "name": "Group1", "subconfig": None},
                            {"blocks": [], "name": "Group2", "subconfig": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "subconfig": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['groups']), 2)

        # Also check via get_group_details
        grps = ch.get_group_details()
        self.assertEqual(len(grps), 2)

    def test_set_config_details_ioc_lists_filled(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True,
                                "macros": [{"name": "TESTMACRO1", "value" : "TEST"}, {"name": "TESTMACRO2",
                                                                                      "value" : 123}],
                                "pvs": [{"name": "TESTPV1", "value": 123}],
                                "pvsets": [{"name": "TESTPVSET1", "enabled": True}],
                                "subconfig": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True,
                                "macros": [{"name": "TESTMACRO3", "value" : "TEST2"}],
                                "pvs": [],
                                "pvsets": [],
                                "subconfig": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "subconfig": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "subconfig": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "IDONTEXIST"], "name": "Group1", "subconfig": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "subconfig": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "subconfig": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['iocs']), 2)
        macros = [y for x in details['iocs'] for y in x['macros']]
        macro_names = [x['name'] for x in macros]
        self.assertTrue("TESTMACRO1" in macro_names)
        self.assertTrue("TESTMACRO3" in macro_names)

    def test_set_config_details_empty_config(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=create_dummy_config())
        new_details = {"iocs": [],
                       "blocks": [],
                       "components": [],
                       "groups": [],
                       "name": "EMPTYCONFIG",
                       "description": ""
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['iocs']), 0)
        self.assertEqual(len(details['blocks']), 0)
        self.assertEqual(len(details['components']), 0)
        self.assertEqual(len(details['groups']), 0)
        self.assertEqual(details['description'], "")
        self.assertEqual(details['name'], "EMPTYCONFIG")

    def test_default_component_is_loaded(self):
        # Arrange
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        # Act
        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        # Assert
        ioc_count = len(ch.get_ioc_names())
        ioc_count_with_default = len(ch.get_ioc_names(True))
        self.assertTrue(ioc_count_with_default > ioc_count)

        comp_count = len(ch.get_component_names())
        comp_count_with_default = len(ch.get_component_names(True))
        self.assertTrue(comp_count_with_default > comp_count)

    def test_cannot_modify_default(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=Configuration(MACROS))

        try:
            ch.save_configuration(DEFAULT_COMPONENT, True)
        except Exception as err:
            self.assertEqual(err.message, "Cannot save over default component")

    def test_clear_config(self):
        ch = ConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_config=None)
        add_block(ch, "TESTBLOCK1", "PV1", "GROUP1", True)
        add_block(ch, "TESTBLOCK2", "PV2", "GROUP2", True)
        add_block(ch, "TESTBLOCK3", "PV3", "GROUP2", True)
        add_block(ch, "TESTBLOCK4", "PV4", "NONE", True)
        blocks = ch.get_blocknames()
        self.assertEquals(len(blocks), 4)
        ch.clear_config()
        blocks = ch.get_blocknames()
        self.assertEquals(len(blocks), 0)

