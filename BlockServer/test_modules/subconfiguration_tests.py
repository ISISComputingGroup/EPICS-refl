import unittest
import os

from config.configuration import Configuration
from config.configuration import GRP_NONE
from config.containers import IOC
from mocks.mock_configuration import MockConfigurationFileManager
from config.xml_converter import ConfigurationXmlConverter
from config.json_converter import ConfigurationJsonConverter

PVPREFIX = 'MYPVPREFIX'

MACROS = {
    "$(MYPVPREFIX)": os.environ[PVPREFIX],
}

#TODO: SubConfiguration

def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


class TestSubconfigurationSequence(unittest.TestCase):
    def setUp(self):
        # Create a new configuration
        self.file_manager = MockConfigurationFileManager()
        self.xml_converter = ConfigurationXmlConverter()
        self.json_converter = ConfigurationJsonConverter()
        # Create a configuration
        self.config = Configuration(MACROS)
        self.config.name = "CONFIG"
        self.config.add_block("CONFIG_BLK1", "PVCB1", "CONFGRP1")
        self.config.add_block("CONFIG_BLK2", "PVCB2", "CONFGRP1")
        self.config.add_block("CONFIG_BLK3", "PVCB3", "CONFGRP2")
        self.config.add_block("CONFIG_BLK4", "PVCB4", GRP_NONE)

    def tearDown(self):
        pass

    def test_adding_subconfig_adds_it_to_subconfig_list(self):
        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"

        # Add it
        self.config.merge_subconfig_in(sub)

        self.assertTrue("TESTSUB".lower() in self.config.subconfigs)

    def test_merge_subconfig_in_with_block_in_none_group(self):
        conf_blks_no = len(self.config.blocks)

        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        sub.add_block("SUB1", "PVS1", GRP_NONE)

        # Add it
        self.config.merge_subconfig_in(sub)

        # Check block is added
        self.assertEqual(len(self.config.blocks), conf_blks_no + 1)
        self.assertTrue("sub1" in self.config.blocks)
        # Check block in none group
        self.assertTrue("SUB1" in self.config.groups[GRP_NONE.lower()].blocks)

    def test_merge_subconfig_in_with_block_in_existing_group(self):
        conf_blks_no = len(self.config.blocks)

        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        sub.add_block("SUB1", "PVS1", "CONFGRP1")

        # Add it
        self.config.merge_subconfig_in(sub)

        # Check block is added
        self.assertEqual(len(self.config.blocks), conf_blks_no + 1)
        self.assertTrue("sub1" in self.config.blocks)
        #Check block in group and is the last entry
        self.assertTrue("SUB1" in self.config.groups["CONFGRP1".lower()].blocks)
        self.assertTrue(self.config.groups["CONFGRP1".lower()].blocks[-1] == "SUB1")

    def test_merge_subconfig_in_with_block_in_new_group(self):
        conf_blks_no = len(self.config.blocks)

        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        sub.add_block("SUB1", "PVS1", "NEWGRP1")

        # Add it
        self.config.merge_subconfig_in(sub)

        # Check block is added
        self.assertEqual(len(self.config.blocks), conf_blks_no + 1)
        self.assertTrue("sub1" in self.config.blocks)
        # Check block in group
        self.assertTrue("SUB1" in self.config.groups["NEWGRP1".lower()].blocks)

    def test_merge_subconfig_in_with_duplicate_block_name_is_ignored(self):
        conf_blks_no = len(self.config.blocks)

        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        # Duplicate block name
        sub.add_block("CONFIG_BLK1", "PVS1", GRP_NONE)

        # Add it
        self.config.merge_subconfig_in(sub)

        # Check block is not added
        self.assertEqual(len(self.config.blocks), conf_blks_no)
        self.assertTrue(self.config.blocks['config_blk1'].pv == "PVCB1")

    def test_merge_subconfig_in_two_subs_no_duplicates(self):
        conf_blks_no = len(self.config.blocks)
        confgrp1_len = len(self.config.groups["CONFGRP1".lower()].blocks)

        sub1 = SubConfiguration(MACROS)
        sub1.name = "TESTSUB1"
        sub1.add_block("SUB1_1", "PVS1", "NONE")
        sub1.add_block("SUB1_2", "PVS1", "NEWGRP1")
        sub1.add_block("SUB1_3", "PVS1", "CONFGRP1")

        sub2 = SubConfiguration(MACROS)
        sub2.name = "TESTSUB2"
        sub2.add_block("SUB2_1", "PVS1", "NONE")
        sub2.add_block("SUB2_2", "PVS1", "NEWGRP1")
        sub2.add_block("SUB2_3", "PVS1", "CONFGRP1")

        # Add them
        self.config.merge_subconfig_in(sub1)
        self.config.merge_subconfig_in(sub2)

        # Check blocks added
        self.assertEqual(len(self.config.blocks), conf_blks_no + 6)
        self.assertTrue("SUB1_1".lower() in self.config.blocks.keys())
        self.assertTrue("SUB1_2".lower() in self.config.blocks.keys())
        self.assertTrue("SUB1_3".lower() in self.config.blocks.keys())
        self.assertTrue("SUB2_1".lower() in self.config.blocks.keys())
        self.assertTrue("SUB2_2".lower() in self.config.blocks.keys())
        self.assertTrue("SUB2_3".lower() in self.config.blocks.keys())
        # Check groups
        self.assertTrue("SUB1_1" in self.config.groups[GRP_NONE.lower()].blocks)
        self.assertTrue("SUB2_1" in self.config.groups[GRP_NONE.lower()].blocks)
        self.assertTrue("SUB1_2" in self.config.groups["NEWGRP1".lower()].blocks)
        self.assertTrue("SUB2_2" in self.config.groups["NEWGRP1".lower()].blocks)
        self.assertTrue("SUB1_3" in self.config.groups["CONFGRP1".lower()].blocks)
        self.assertTrue("SUB2_3" in self.config.groups["CONFGRP1".lower()].blocks)
        self.assertTrue(len(self.config.groups["CONFGRP1".lower()].blocks) == confgrp1_len + 2)

    def test_merge_subconfig_in_two_subs_with_duplicates(self):
        confgrp1_len = len(self.config.groups["CONFGRP1".lower()].blocks)

        sub1 = SubConfiguration(MACROS)
        sub1.name = "TESTSUB1"
        sub1.add_block("SUB1_1", "PVS1", "NONE")
        sub1.add_block("SUB1_2", "PVS1", "NEWGRP1")
        sub1.add_block("SUB_DUP", "PVS1", "CONFGRP1")

        sub2 = SubConfiguration(MACROS)
        sub2.name = "TESTSUB2"
        sub2.add_block("SUB2_1", "PVS1", "NONE")
        sub2.add_block("SUB2_2", "PVS1", "NEWGRP1")
        sub2.add_block("SUB_DUP", "PVS2", "CONFGRP1")   # This blocks should be ignored

        # Add them
        self.config.merge_subconfig_in(sub1)
        self.config.merge_subconfig_in(sub2)

        self.assertEqual(len(self.config.groups["CONFGRP1".lower()].blocks), confgrp1_len + 1)
        self.assertTrue(self.config.blocks['SUB_DUP'.lower()].pv == "PVS1")

    # def test_merge_subconfig_in_and_get_groups_xml(self):
    #     sub = SubConfiguration(MACROS, self.file_manager)
    #     sub.config_name = "TESTSUB"
    #     sub.add_block("SUB1", "PVS1", "CONFGRP1")
    #     sub.add_block("SUB2", "PVS2", "SUBGRP1")
    #
    #     #Add it
    #     self.config.merge_subconfig_in(sub)
    #
    #     #Check xml is okay
    #     ans_should_be = \
    #         """<?xml version="1.0" ?>
    #         <groups>
    #             <group name="CONFGRP1">
    #                 <block name="CONFIG_BLK1"/>
    #                 <block name="CONFIG_BLK2"/>
    #                 <block name="SUB1"/>
    #             </group>
    #             <group name="CONFGRP2">
    #                 <block name="CONFIG_BLK3"/>
    #             </group>
    #             <group name="SUBGRP1">
    #                 <block name="SUB2"/>
    #             </group>
    #         </groups>"""
    #     grps = self.config.get_groups_xml()
    #     self.assertEqual(strip_out_whitespace(grps), strip_out_whitespace(ans_should_be))
    #
    # def test_merge_subconfig_in_remove_and_get_groups_xml(self):
    #     sub = SubConfiguration(MACROS, self.file_manager)
    #     sub.config_name = "TESTSUB"
    #     sub.add_block("SUB1", "PVS1", "CONFGRP1")
    #     sub.add_block("SUB2", "PVS2", "SUBGRP1")
    #
    #     #Add it
    #     self.config.merge_subconfig_in(sub)
    #     #Remove it
    #     self.config.remove_subconfig("TESTSUB")
    #
    #     #Check xml is okay
    #     ans_should_be = \
    #         """<?xml version="1.0" ?>
    #         <groups>
    #             <group name="CONFGRP1">
    #                 <block name="CONFIG_BLK1"/>
    #                 <block name="CONFIG_BLK2"/>
    #             </group>
    #             <group name="CONFGRP2">
    #                 <block name="CONFIG_BLK3"/>
    #             </group>
    #         </groups>"""
    #     grps = self.config.get_groups_xml()
    #     self.assertEqual(strip_out_whitespace(grps), strip_out_whitespace(ans_should_be))

    def test_merge_subconfig_in_with_iocs(self):
        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        sub.iocs['IOC1'] = IOC('IOC1', sub.name)
        sub.iocs['IOC2'] = IOC('IOC2', sub.name)
        sub.iocs['IOC3'] = IOC('IOC3', sub.name)

        #Add it
        self.config.merge_subconfig_in(sub)

        #Check iocs added
        self.assertEqual(len(self.config.iocs), 3)
        self.assertTrue("IOC1" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC1"].subconfig == sub.name)
        self.assertTrue("IOC2" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC2"].subconfig == sub.name)
        self.assertTrue("IOC3" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC3"].subconfig == sub.name)

    def test_merge_subconfig_in_with_duplicate_ioc(self):
        sub = SubConfiguration(MACROS)
        sub.name = "TESTSUB"
        sub.iocs['IOC1'] = IOC('IOC1', sub.name)
        sub.iocs['IOC2'] = IOC('IOC2', sub.name)
        sub.iocs['IOC3'] = IOC('IOC3', sub.name)

        #Add ioc to config
        self.config.iocs['IOC1'] = IOC('IOC1')

        #Add it
        self.config.merge_subconfig_in(sub)

        #Check iocs added
        self.assertEqual(len(self.config.iocs), 3)
        self.assertTrue("IOC1" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC1"].subconfig is None)
        self.assertTrue("IOC2" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC2"].subconfig == sub.name)
        self.assertTrue("IOC3" in self.config.iocs)
        self.assertTrue(self.config.iocs["IOC3"].subconfig == sub.name)


if __name__ == '__main__':
    #start blockserver
    unittest.main()

