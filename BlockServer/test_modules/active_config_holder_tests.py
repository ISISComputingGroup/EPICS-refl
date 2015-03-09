import unittest
import os
import shutil
import json

from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.config.configuration import Configuration


CONFIG_PATH = "./test_configs/"
BASE_PATH = "./example_base/"

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}


# Helper methods
def quick_block_to_json(name, pv, group, local=True):
    data = {'name': name, 'pv': pv, 'group': group, 'local': local}
    return data


def add_block(cs, data):
    cs.add_block(data)


def get_groups_and_blocks(jsondata):
    groups = json.loads(jsondata)
    return groups


def create_grouping(groups):
    struct = []
    for grp, blocks in groups.iteritems():
        d = dict()
        d["name"] = grp
        d["blocks"] = blocks
        struct.append(d)    
    ans = json.dumps(struct)
    return ans


# Note that the ActiveConfigServerManager contains an instance of the Configuration class and hands a lot of
#   work off to this object. Rather than testing whether the functionality in the configuration class works
#   correctly (e.g. by checking that a block has been edited properly after calling configuration.edit_block),
#   we should instead test that ActiveConfigServerManager passes the correct parameters to the Configuration object.
#   We are testing that ActiveConfigServerManager correctly interfaces with Configuration, not testing the
#   functionality of Configuration, which is done in Configuration's own suite of tests.
class TestActiveConfigHolderSequence(unittest.TestCase):
    def setUp(self):
        # Create components folder and copying DEFAULT_COMPONENT fileIO into it
        path = os.path.abspath(CONFIG_PATH)
        os.mkdir(path)
        component_path = path + "/components/"
        os.mkdir(component_path)
        shutil.copytree(BASE_PATH, component_path + "/" + DEFAULT_COMPONENT)

        # Create in test mode
        self.activech = ActiveConfigHolder(CONFIG_PATH, MACROS, None, "archive.xml", test_mode=True)

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(CONFIG_PATH)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_add_ioc(self):
        cs = self.activech
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_start_config_iocs(self):
        cs = self.activech
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")
        cs._start_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "RUNNING")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "RUNNING")

    def test_stop_config_iocs(self):
        cs = self.activech
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")
        cs._start_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "RUNNING")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "RUNNING")
        cs.stop_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")

    def test_restart_ioc(self):
        cs = self.activech
        cs.stop_iocs(["SIMPLE1"])
        cs.restart_iocs(["SIMPLE1"])
        self.assertTrue(cs.get_ioc_state("SIMPLE1") == "RUNNING")

    def test_save_config(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        try:
            cs.save_active("TEST_CONFIG")
        except Exception:
            self.fail("test_save_config raised Exception unexpectedly!")

    def test_load_config(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        cs.save_active("TEST_CONFIG")
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEquals(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_active("TEST_CONFIG")
        blocks = cs.get_blocknames()
        self.assertEquals(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_notexistant_config(self):
        cs = self.activech
        self.assertRaises(Exception, lambda _: cs.load_active("DOES_NOT_EXIST"))

    def test_save_as_subconfig(self):
        cs = self.activech
        try:
            cs.save_active("TEST_CONFIG1", as_comp=True)
        except Exception:
            self.fail("test_save_as_subconfig raised Exception unexpectedly!")

    def test_save_config_for_sub_config(self):
        cs = self.activech
        cs.save_active("TEST_CONFIG1", as_comp=True)
        try:
            cs.save_active("TEST_CONFIG1")
        except Exception:
            self.fail("test_save_config_for_subconfig raised Exception unexpectedly!")

    def test_load_subconfig(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        cs.save_active("TEST_SUBCONFIG", as_comp=True)
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_active("TEST_SUBCONFIG", True)
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_last_config(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        cs.save_active("TEST_CONFIG")
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_last_config()
        grps = cs.get_group_details()
        self.assertTrue(len(grps) == 3)
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_last_config_subconfig(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        cs.save_active("TEST_SUBCONFIG", as_comp=True)
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_last_config()
        grps = cs.get_group_details()
        self.assertTrue(len(grps) == 3)
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_get_runcontrol_settings_empty(self):
        cs = self.activech
        cs.create_runcontrol_pvs()
        ans = cs.get_runcontrol_settings()
        self.assertTrue(len(ans) == 0)

    def test_get_runcontrol_settings_blocks(self):
        cs = self.activech
        add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.create_runcontrol_pvs()
        ans = cs.get_runcontrol_settings()
        self.assertTrue(len(ans) == 4)
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] is None)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] is None)
        self.assertTrue(not ans["TESTBLOCK1"]["ENABLE"])

    def test_get_runcontrol_settings_blocks_limits(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        ans = cs.get_runcontrol_settings()
        self.assertTrue(len(ans) == 1)
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] == 5)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] == -5)
        self.assertTrue(ans["TESTBLOCK1"]["ENABLE"])

    def test_get_out_of_range_pvs_multiple(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 5, 'highlimit': 10}
        add_block(cs, data)
        data = {'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 10, 'highlimit': 15}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        # Values are 0 by default, so they should be out of range
        ans = cs.get_out_of_range_pvs()
        self.assertEqual(len(ans), 2)
        self.assertTrue("TESTBLOCK1" in ans)
        self.assertTrue("TESTBLOCK2" in ans)

    def test_get_out_of_range_pvs_single(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 5, 'highlimit': 10}
        add_block(cs, data)
        data = {'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 10, 'highlimit': 15}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        # Values are 0 by default, so they should be out of range if enabled
        ans = cs.get_out_of_range_pvs()
        self.assertEqual(len(ans), 1)
        self.assertTrue("TESTBLOCK1" in ans)

    def test_get_out_of_range_pvs_none(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 5, 'highlimit': 10}
        add_block(cs, data)
        data = {'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 10, 'highlimit': 15}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        ans = cs.get_out_of_range_pvs()
        self.assertEqual(len(ans), 0)

    def test_set_runcontrol_settings(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        ans = cs.get_runcontrol_settings()
        ans["TESTBLOCK1"]["LOW"] = 0
        ans["TESTBLOCK1"]["HIGH"] = 10
        ans["TESTBLOCK1"]["ENABLE"] = False
        cs.set_runcontrol_settings(ans)
        ans = cs.get_runcontrol_settings()
        self.assertEqual(ans["TESTBLOCK1"]["HIGH"], 10)
        self.assertEqual(ans["TESTBLOCK1"]["LOW"], 0)
        self.assertTrue(not ans["TESTBLOCK1"]["ENABLE"])

    def test_save_config_and_load_config_restore_runcontrol(self):
        cs = self.activech
        data = {'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5,
                'save_rc': True}
        add_block(cs, data)
        cs.create_runcontrol_pvs()
        cs.create_runcontrol_pvs()
        cs.save_active("TESTCONFIG1")
        cs.load_active("TESTCONFIG1")
        ans = cs.get_runcontrol_settings()
        self.assertEqual(ans["TESTBLOCK1"]["HIGH"], 5)
        self.assertEqual(ans["TESTBLOCK1"]["LOW"], -5)
        self.assertTrue(ans["TESTBLOCK1"]["ENABLE"])


if __name__ == '__main__':
    # Run tests
    unittest.main()