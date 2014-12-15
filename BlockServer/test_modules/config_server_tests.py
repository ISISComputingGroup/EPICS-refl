import unittest
import os
import shutil
import json
from config_server import ConfigServerManager

from mocks.mock_configuration import MockConfiguration


MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}


def quick_block_to_json(name, pv, group, local=True):
    data = [{'name': name, 'pv': pv, 'group': group, 'local': local}]
    return json.dumps(data)
    

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


# Note that the ConfigServerManager contains an instance of the Configuration class and hands a lot of
#   work off to this object. Rather than testing whether the functionality in the configuration class works
#   correctly (e.g. by checking that a block has been edited properly after calling configuration.edit_block),
#   we should instead test that ConfigServerManager passes the correct parameters to the Configuration object. We are
#   testing that ConfigServerManager correctly interfaces with Configuration, not testing the functionality of
#   Configuration, which is done in Configuration's own suite of tests.
class TestConfigServerSequence(unittest.TestCase):
    def setUp(self):
        # Create in test mode
        self.configserver = ConfigServerManager("./test_configs/", MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                                test_mode=True)

    def tearDown(self):
        # Delete any configs created as part of the test
        config_folder = self.configserver.get_config_folder()
        path = os.path.abspath(config_folder)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_remove_blocks_multiple(self):
        # arrange
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))

        # act
        blocks = ["TESTBLOCK1", "TESTBLOCK2"]
        cs.remove_blocks(json.dumps(blocks))

        # assert
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEquals(len(blocks), 2)
        self.assertTrue("TESTBLOCK3" in blocks)
        self.assertTrue("TESTBLOCK4" in blocks)

    def test_getting_blocks_json_with_no_blocks_returns_empty_list(self):
        # arrange
        cs = self.configserver
        # act
        blocks = json.loads(cs.get_blocknames_json())
        # assert
        self.assertEqual(len(blocks), 0)

    def test_clear_config(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEquals(len(blocks), 4)
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEquals(len(blocks), 0)

    def test_add_ioc(self):
        cs = self.configserver
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_add_ioc_non_existant(self):
        cs = self.configserver
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        self.assertRaises(Exception, cs.add_iocs, json.dumps(["RERE"]))

    def test_start_config_iocs(self):
        cs = self.configserver
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")
        cs._start_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "RUNNING")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "RUNNING")

    def test_stop_config_iocs(self):
        cs = self.configserver
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")
        cs._start_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "RUNNING")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "RUNNING")
        cs.stop_config_iocs()
        self.assertEqual(cs.get_ioc_state("SIMPLE1"), "SHUTDOWN")
        self.assertEqual(cs.get_ioc_state("SIMPLE2"), "SHUTDOWN")

    def test_restart_ioc(self):
        cs = self.configserver
        cs.stop_iocs(json.dumps(["SIMPLE1"]))
        cs.restart_iocs(json.dumps(["SIMPLE1"]))
        self.assertTrue(cs.get_ioc_state("SIMPLE1") == "RUNNING")

    def test_remove_ioc(self):
        cs = self.configserver
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        cs.remove_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        self.assertTrue(not "SIMPLE1" in iocs)
        self.assertTrue(not "SIMPLE2" in iocs)

    def test_save_config(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        try:
            cs.save_config(json.dumps("TEST_CONFIG"))
        except Exception:
            self.fail("test_save_config raised Exception unexpectedly!")

    def test_load_config(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_config(json.dumps("TEST_CONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEquals(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.load_config(json.dumps("TEST_CONFIG"))
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEquals(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_notexistant_config(self):
        cs = self.configserver
        self.assertRaises(Exception, lambda _: cs.load_config(json.dumps("DOES_NOT_EXIST")))

    def test_get_configs_string(self):
        cs = self.configserver
        confs = json.loads(cs.get_configs_json())
        self.assertEqual(len(confs), 0)
        cs.save_config(json.dumps("TEST_CONFIG1"))
        cs.save_config(json.dumps("TEST_CONFIG2"))
        cs.save_config(json.dumps("TEST_CONFIG3"))
        confs = json.loads(cs.get_configs_json())
        self.assertEqual(len(confs), 3)
        self.assertTrue("TEST_CONFIG1" in confs)
        self.assertTrue("TEST_CONFIG2" in confs)
        self.assertTrue("TEST_CONFIG3" in confs)

    def test_get_block_prefix(self):
        cs = self.configserver
        self.assertEquals(json.loads(cs.get_block_prefix_json()), MACROS["$(MYPVPREFIX)"] + "BLOCK_PREFIX:")

    def test_get_subconfigs_json(self):
        cs = self.configserver
        self.assertTrue(cs.get_conf_subconfigs_json() == "[]")

    def test_get_config_name(self):
        cs = self.configserver
        name = json.loads(cs.get_config_name_json())
        self.assertTrue(name == "")
        cs.save_config(json.dumps("TESTCONFIG1"))
        name = json.loads(cs.get_config_name_json())
        self.assertTrue(name == "TESTCONFIG1")

    def test_get_blocks(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        self.assertTrue("TESTBLOCK1".lower() in cs.get_blocks().keys())
        self.assertTrue("TESTBLOCK2".lower() in cs.get_blocks().keys())

    def test_edit_blocks_json(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        # Edit
        edit_data = [{'name': "TESTBLOCK1", 'pv': "PV3", 'new_name': "TESTBLOCK3"}]
        cs.edit_blocks_json(json.dumps(edit_data))

        self.assertEqual(cs.get_blocks()["TESTBLOCK3".lower()].pv, "PV3")

    def test_edit_blocks_json_no_data_raises(self):
        cs = self.configserver
        self.assertRaises(Exception, cs.edit_blocks_json, None)

    def test_edit_blocks_json_missing_args_raises(self):
        cs = self.configserver
        # No name
        data = [{'pv': "PV1", 'group': "GROUP1", 'local': False, 'visible': False}]
        self.assertRaises(Exception, cs.edit_blocks_json, data)

    def test_edit_blocks_json_multiple(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        # Edit
        edit_data = [{'name': "TESTBLOCK1", 'pv': "PV3"},
                     {'name': "TESTBLOCK2", 'pv': "PV4"}]
        cs.edit_blocks_json(json.dumps(edit_data))

        self.assertEqual(cs.get_blocks()["TESTBLOCK1".lower()].pv, "PV3")
        self.assertEqual(cs.get_blocks()["TESTBLOCK2".lower()].pv, "PV4")

    def test_add_block_json(self):
        cs = self.configserver
        data = [{"name": "TESTBLOCK1", 'pv': "PV1", 'group': "GROUP1", 'local': False, 'visible': False}]
        cs.add_blocks_json(json.dumps(data))

        self.assertTrue("TESTBLOCK1".lower() in cs.get_blocks().keys())
        self.assertEqual(cs.get_blocks()["TESTBLOCK1".lower()].pv, "PV1")
        self.assertEqual(cs.get_blocks()["TESTBLOCK1".lower()].local, False)
        self.assertEqual(cs.get_blocks()["TESTBLOCK1".lower()].visible, False)

    def test_add_block_json_multiple(self):
        cs = self.configserver
        data = [{"name": "TESTBLOCK1", 'pv': "PV1", 'group': "GROUP1", 'local': False, 'visible': False},
                {"name": "TESTBLOCK2", 'pv': "PV2", 'group': "GROUP2", 'local': False, 'visible': False}]
        cs.add_blocks_json(json.dumps(data))

        self.assertTrue("TESTBLOCK1".lower() in cs.get_blocks().keys())
        self.assertTrue("TESTBLOCK2".lower() in cs.get_blocks().keys())
        self.assertEqual(len(cs.get_blocks()), 2)

    def test_add_block_json_no_data_raises(self):
        cs = self.configserver
        self.assertRaises(Exception, cs.add_blocks_json, None)

    def test_add_block_json_missing_args_raises(self):
        cs = self.configserver
        # No name
        data = [{'pv': "PV1", 'group': "GROUP1", 'local': False, 'visible': False}]
        self.assertRaises(Exception, cs.add_blocks_json, data)
        # No read pv
        data = [{"name": "TESTBLOCK1", 'group': "GROUP1", 'local': False, 'visible': False}]
        self.assertRaises(Exception, cs.add_blocks_json, data)

    def test_get_subconfigs_string(self):
        cs = self.configserver
        confs = json.loads(cs.get_subconfigs_json())
        self.assertEqual(len(confs), 0)
        cs.save_as_subconfig(json.dumps("TEST_CONFIG1"))
        cs.save_as_subconfig(json.dumps("TEST_CONFIG2"))
        cs.save_as_subconfig(json.dumps("TEST_CONFIG3"))
        confs = json.loads(cs.get_subconfigs_json())
        self.assertEqual(len(confs), 3)
        self.assertTrue("TEST_CONFIG1" in confs)
        self.assertTrue("TEST_CONFIG2" in confs)
        self.assertTrue("TEST_CONFIG3" in confs)

    def test_dump_status(self):
        cs = self.configserver
        try:
            cs.dump_status()
        except Exception:
            self.fail("test_dump_status raised Exception unexpectedly!")

    def test_autosave_config(self):
        cs = self.configserver
        try:
            cs.autosave_config()
        except Exception:
            self.fail("test_autosave_config raised Exception unexpectedly!")

    def test_save_as_subconfig(self):
        cs = self.configserver
        try:
            cs.save_as_subconfig(json.dumps("TEST_CONFIG1"))
        except Exception:
            self.fail("test_save_as_subconfig raised Exception unexpectedly!")

    def test_save_config_for_sub_config(self):
        cs = self.configserver
        cs.save_as_subconfig(json.dumps("TEST_CONFIG1"))
        try:
            cs.save_config(json.dumps("TEST_CONFIG1"))
        except Exception:
            self.fail("test_save_config_for_subconfig raised Exception unexpectedly!")

    def test_load_subconfig(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.load_config(json.dumps("TEST_SUBCONFIG"), True)
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_add_subconfig(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.add_subconfigs(json.dumps(["TEST_SUBCONFIG"]))
        grps = get_groups_and_blocks(cs.get_groupings_json())
        self.assertEqual(len(grps), 3)
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_remove_subconfig(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.add_subconfigs(json.dumps(["TEST_SUBCONFIG"]))
        grps = get_groups_and_blocks(cs.get_groupings_json())
        self.assertTrue(len(grps) == 3)
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        cs.remove_subconfigs(json.dumps(["TEST_SUBCONFIG"]))
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)

    def test_load_last_config(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_config(json.dumps("TEST_CONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.load_last_config()
        grps = get_groups_and_blocks(cs.get_groupings_json())
        self.assertTrue(len(grps) == 3)
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_last_config_subconfig(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))
        cs.clear_config()
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 0)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertEqual(len(iocs), 0)
        cs.load_last_config()
        grps = get_groups_and_blocks(cs.get_groupings_json())
        self.assertTrue(len(grps) == 3)
        blocks = json.loads(cs.get_blocknames_json())
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = json.loads(cs.get_config_iocs_json())
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_get_runcontrol_settings_empty(self):
        cs = self.configserver
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertTrue(len(ans) == 0)

    def test_get_runcontrol_settings_blocks(self):
        cs = self.configserver
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertTrue(len(ans) == 4)
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] is None)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] is None)
        self.assertTrue(not ans["TESTBLOCK1"]["ENABLE"])

    def test_get_runcontrol_settings_blocks_limits(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertTrue(len(ans) == 1)
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] == 5)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] == -5)
        self.assertTrue(ans["TESTBLOCK1"]["ENABLE"])

    def test_get_out_of_range_pvs_multiple(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 5, 'highlimit': 10}]
        cs.add_blocks_json(json.dumps(data))
        data = [{'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 10, 'highlimit': 15}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        #Values are 0 by default, so they should be out of range
        ans = json.loads(cs.get_out_of_range_pvs())
        self.assertTrue(len(ans) == 2)
        self.assertTrue("TESTBLOCK1" in ans)
        self.assertTrue("TESTBLOCK2" in ans)

    def test_get_out_of_range_pvs_single(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': 5, 'highlimit': 10}]
        cs.add_blocks_json(json.dumps(data))
        data = [{'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 10, 'highlimit': 15}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        # Values are 0 by default, so they should be out of range if enabled
        ans = json.loads(cs.get_out_of_range_pvs())
        self.assertTrue(len(ans) == 1)
        self.assertTrue("TESTBLOCK1" in ans)

    def test_get_out_of_range_pvs_none(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 5, 'highlimit': 10}]
        cs.add_blocks_json(json.dumps(data))
        data = [{'name': "TESTBLOCK2", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 10, 'highlimit': 15}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_out_of_range_pvs())
        self.assertTrue(len(ans) == 0)

    def test_set_runcontrol_settings(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        ans["TESTBLOCK1"]["LOW"] = 0
        ans["TESTBLOCK1"]["HIGH"] = 10
        ans["TESTBLOCK1"]["ENABLE"] = False
        cs.set_runcontrol_settings_json(json.dumps(ans))
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertEqual(ans["TESTBLOCK1"]["HIGH"], 10)
        self.assertEqual(ans["TESTBLOCK1"]["LOW"], 0)
        self.assertTrue(not ans["TESTBLOCK1"]["ENABLE"])

    def test_save_config_and_load_config_restore_runcontrol(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5,
                'save_rc': True}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        cs.create_runcontrol_pvs()
        cs.save_config(json.dumps("TESTCONFIG1"))
        cs.load_config(json.dumps("TESTCONFIG1"))
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertEqual(ans["TESTBLOCK1"]["HIGH"], 5)
        self.assertEqual(ans["TESTBLOCK1"]["LOW"], -5)
        self.assertTrue(ans["TESTBLOCK1"]["ENABLE"])

    def test_edit_blocks_json_runcontrol_settings(self):
        cs = self.configserver
        data = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}]
        cs.add_blocks_json(json.dumps(data))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] == 5)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] == -5)
        self.assertTrue(ans["TESTBLOCK1"]["ENABLE"])
        newdata = [{'name': "TESTBLOCK1", 'pv': "PV1", 'runcontrol': False, 'lowlimit': 0, 'highlimit': 10}]
        cs.edit_blocks_json(json.dumps(newdata))
        cs.set_runcontrol_settings_json(json.dumps(ans))
        cs.create_runcontrol_pvs()
        ans = json.loads(cs.get_runcontrol_settings_json())
        self.assertEqual(ans["TESTBLOCK1"]["HIGH"], 10)
        self.assertEqual(ans["TESTBLOCK1"]["LOW"], 0)
        self.assertTrue(not ans["TESTBLOCK1"]["ENABLE"])

    def test_get_config_details_for_current_config(self):
        cs = self.configserver
        # Create an empty subconfig
        cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))
        cs.clear_config()

        cs.add_blocks_json(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        cs.add_blocks_json(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        cs.add_iocs(json.dumps(["SIMPLE1", "SIMPLE2"]))
        cs.add_subconfigs(json.dumps(["TEST_SUBCONFIG"]))
        cs.save_config(json.dumps("TEST_CONFIG"))

        js = cs.get_config_details()
        config = json.loads(js)
        self.assertEqual(len(config['blocks']), 4)
        blks = [x['name'] for x in config['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertEqual(config['blocks'][0]['pv'], "PV1")
        self.assertIsNone(config['blocks'][0]['subconfig'])
        self.assertEqual(config['blocks'][0]['local'], True)
        self.assertEqual(len(config['groups']), 3)
        self.assertEqual(config['groups'][0]['name'], "GROUP1")
        self.assertEqual(config['groups'][1]['name'], "GROUP2")
        self.assertEqual(config['groups'][2]['name'], "NONE")
        self.assertTrue("TESTBLOCK1" in config['groups'][0]['blocks'])
        self.assertTrue("TESTBLOCK2" in config['groups'][1]['blocks'])
        self.assertTrue("TESTBLOCK3" in config['groups'][1]['blocks'])
        self.assertTrue("TESTBLOCK4" in config['groups'][2]['blocks'])
        self.assertEqual(len(config['iocs']), 2)
        iocs = [x['name'] for x in config['iocs']]
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        comps = [x['name'] for x in config['components']]
        self.assertTrue("TEST_SUBCONFIG" in comps)

    def test_set_config_details_for_current_config(self):
        cs = self.configserver
        data = {"iocs":
                [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": {}, "pvs": {}, "pvsets": {}, "subconfig": None},
                    {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": {}, "pvs": {}, "pvsets": {}, "subconfig": None}],
                "blocks":
                    [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "subconfig": None, "visible": True},
                     {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "subconfig": None, "visible": True},
                     {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "subconfig": None, "visible": True}],
                "components":
                    [],
                "groups":
                    [{"blocks": ["TESTBLOCK1"], "name": "Group1", "subconfig": None},
                     {"blocks": ["TESTBLOCK2"], "name": "Group2", "subconfig": None},
                     {"blocks": ["TESTBLOCK3"], "name": "NONE", "subconfig": None}],
                "name": "TESTCONFIG"
        }
        cs.set_config_details(json.dumps(data))

        js = cs.get_config_details()
        config = json.loads(js)

        self.assertEqual(len(config['blocks']), 3)
        blks = [x['name'] for x in config['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertTrue("TESTBLOCK2" in blks)
        self.assertTrue("TESTBLOCK3" in blks)
        self.assertEqual(len(config['groups']), 3)
        self.assertEqual(config['groups'][0]['name'], "Group1")
        self.assertEqual(config['groups'][1]['name'], "Group2")
        self.assertEqual(config['groups'][2]['name'], "NONE")
        self.assertTrue("TESTBLOCK1" in config['groups'][0]['blocks'])
        self.assertTrue("TESTBLOCK2" in config['groups'][1]['blocks'])
        self.assertTrue("TESTBLOCK3" in config['groups'][2]['blocks'])
        self.assertEqual(len(config['iocs']), 2)
        iocs = [x['name'] for x in config['iocs']]
        self.assertTrue("TESTSIMPLE1" in iocs)
        self.assertTrue("TESTSIMPLE2" in iocs)


if __name__ == '__main__':
    # Run tests
    unittest.main()