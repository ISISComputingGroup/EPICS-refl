import os
import re
import unittest
from xml.etree import ElementTree
from collections import OrderedDict

from config.containers import Group, Block, IOC, MetaData
from config.xml_converter import ConfigurationXmlConverter


PVPREFIX = 'MYPVPREFIX'
MACROS = {"$(MYPVPREFIX)": os.environ[PVPREFIX]}

BLOCKS_XML = u"""
<?xml version="1.0" ?>
<blocks xmlns="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:blk="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
    <block>
        <name>TESTBLOCK1</name>
        <read_pv>TESTPV1</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_save>True</rc_save>
        <rc_enabled>False</rc_enabled>
    </block>
    <block>
        <name>TESTBLOCK2</name>
        <read_pv>TESTPV2</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_save>True</rc_save>
        <rc_enabled>False</rc_enabled>
    </block>
    <block>
        <name>TESTBLOCK3</name>
        <read_pv>TESTPV3</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_save>True</rc_save>
        <rc_enabled>False</rc_enabled>
    </block>
    <block>
        <name>TESTBLOCK4</name>
        <read_pv>TESTPV4</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_save>True</rc_save>
        <rc_enabled>False</rc_enabled>
    </block>
</blocks>"""

GROUPS_XML = u"""
<?xml version="1.0" ?>
<groups xmlns="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:grp="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
    <group name="TESTGROUP1">
        <block name="TESTBLOCK1"/>
        <block name="TESTBLOCK2"/>
    </group>
    <group name="TESTGROUP2">
        <block name="TESTBLOCK3"/>
        <block name="TESTBLOCK4"/>
    </group>
</groups>"""

IOCS_XML = u"""
<?xml version="1.0" ?>
<iocs xmlns="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:ioc="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
    <ioc autostart="true" name="TESTIOC1" restart="false" simlevel="recsim">
        <macros>
            <macro name="TESTIOC1MACRO" value="1"/>
        </macros>
        <pvs>
            <pv name="TESTIOC1PV" value="1"/>
        </pvs>
        <pvsets>
            <pvset enabled="True" name="TESTIOC1PVSET"/>
        </pvsets>
    </ioc>
    <ioc autostart="true" name="TESTIOC2" restart="false" simlevel="devsim">
        <macros>
            <macro name="TESTIOC2MACRO" value="2"/>
        </macros>
        <pvs>
            <pv name="TESTIOC2PV" value="2"/>
        </pvs>
        <pvsets>
            <pvset enabled="True" name="TESTIOC2PVSET"/>
        </pvsets>
    </ioc>
</iocs>"""

META_XML = u"""<?xml version="1.0" ?>
<meta>
<description>A test description</description>
<synoptic>TEST_SYNOPTIC</synoptic>
<edits>
<edit>1992-02-07</edit>
</edits>
</meta>
"""

CONFIG_XML = u"""<?xml version="1.0" ?>
<ioc_configs>
	<ioc_config name="TESTIOC1">
	    <config_part>
            <macros>
                <macro description="DESC TESTIOC1MAC1" name="TESTIOC1MAC1" pattern="PAT1"/>
                <macro description="DESC TESTIOC1MAC2" name="TESTIOC1MAC2" pattern="PAT1"/>
            </macros>
            <pvsets>
                <pvset description="DESC TESTIOC1PV1" name="TESTIOC1PV1"/>
                <pvset description="DESC TESTIOC1PV2" name="TESTIOC1PV2"/>
            </pvsets>
	    </config_part>
	</ioc_config>
	<ioc_config name="TESTIOC2">
	    <config_part>
            <macros>
                <macro description="DESC TESTIOC2MAC1" name="TESTIOC2MAC1" pattern="PAT2"/>
                <macro description="DESC TESTIOC2MAC2" name="TESTIOC2MAC2" pattern="PAT2"/>
            </macros>
            <pvsets>
                <pvset description="DESC TESTIOC2PV1" name="TESTIOC2PV1"/>
                <pvset description="DESC TESTIOC2PV2" name="TESTIOC2PV2"/>
            </pvsets>
        </config_part>
	</ioc_config>
</ioc_configs>"""

def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")

def strip_out_namespace(string):
    return re.sub(' xmlns="[^"]+"', '', string, count=1)

BLOCKS_XML = strip_out_whitespace(BLOCKS_XML)
GROUPS_XML = strip_out_whitespace(GROUPS_XML)
IOCS_XML = strip_out_whitespace(IOCS_XML)
CONFIG_XML = strip_out_whitespace(CONFIG_XML)

def make_blocks():
    blocks = OrderedDict()
    for i in range(1, 5):
        num = str(i)
        new_block_args = ["TESTBLOCK"+num, "TESTPV"+num, True, True]
        key = new_block_args[0].lower()
        blocks[key] = Block(*new_block_args)
    return blocks


def make_groups():
    groups = OrderedDict()
    block_num = 1
    for i in range(1, 3):
        name = "TESTGROUP" + str(i)
        groups[name.lower()] = Group(name)
        groups[name.lower()].blocks = ["TESTBLOCK" + str(block_num), "TESTBLOCK" + str(block_num+1)]
        block_num += 2
    return groups


def make_iocs():
    iocs = OrderedDict()
    SIM_LEVELS = ['recsim', 'devsim']
    for i in range(1, 3):
        iocs["TESTIOC" + str(i)] = IOC("TESTIOC" + str(i))
        iocs["TESTIOC" + str(i)].autostart = True
        iocs["TESTIOC" + str(i)].restart = False
        iocs["TESTIOC" + str(i)].simlevel = SIM_LEVELS[i-1]
        iocs["TESTIOC" + str(i)].macros["TESTIOC" + str(i) + "MACRO"] = {"value": i}
        iocs["TESTIOC" + str(i)].pvs["TESTIOC" + str(i) + "PV"] = {"value": i}
        iocs["TESTIOC" + str(i)].pvsets["TESTIOC" + str(i) + "PVSET"] = {"enabled": True}
    return iocs

def make_meta():
    meta = MetaData('Test', description='A test description', synoptic="TEST_SYNOPTIC")
    meta.history = ["1992-02-07"]
    return meta

class TestConfigurationXmlConverterSequence(unittest.TestCase):
    def setUp(self):
        # Create a new XML converter
        self.xml_converter = ConfigurationXmlConverter()

    def tearDown(self):
        pass

    def test_blocks_to_xml_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        blocks = make_blocks()

        # act
        blocks_xml = xc.blocks_to_xml(blocks, MACROS)
        blocks_xml = strip_out_whitespace(blocks_xml)

        #assert
        self.maxDiff = None
        self.assertEqual(blocks_xml, BLOCKS_XML)

    def test_groups_to_xml_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        groups = make_groups()

        # act
        groups_xml = xc.groups_to_xml(groups)
        groups_xml = strip_out_whitespace(groups_xml)

        #assert
        self.assertEqual(groups_xml, GROUPS_XML)

    def test_iocs_to_xml_converts_correctly(self):
        # arrange
        self.maxDiff = None
        xc = self.xml_converter
        iocs = make_iocs()

        #act
        iocs_xml = xc.iocs_to_xml(iocs)
        iocs_xml = strip_out_whitespace(iocs_xml)

        #assert
        self.assertEqual(iocs_xml.strip(), IOCS_XML.strip())

    def test_meta_to_xml_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        meta = make_meta()

        #act
        meta_xml = xc.meta_to_xml(meta)
        meta_xml = strip_out_whitespace(meta_xml)

        #assert
        self.assertEqual(meta_xml.strip(), META_XML.strip())

    def test_xml_to_blocks_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        blocks = OrderedDict()
        groups = {"none": Group("NONE")}
        root_xml = ElementTree.fromstring(strip_out_namespace(BLOCKS_XML))

        # act
        xc.blocks_from_xml(root_xml, blocks, groups)
        expected_blocks = make_blocks()

        # assert
        self.assertEqual(len(blocks), len(expected_blocks))
        for key, value in blocks.iteritems():
            self.assertTrue(key in expected_blocks)
            expected = expected_blocks[key]
            self.assertEqual(value.name, expected.name)
            self.assertEqual(value.pv, expected.pv)
            self.assertEqual(value.local, expected.local)

    def test_xml_string_to_groups_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        groups = OrderedDict()
        blocks = OrderedDict()

        # act
        xc.groups_from_xml_string(strip_out_namespace(GROUPS_XML), groups, blocks)
        expected_groups = make_groups()

        # assert
        self.assertEqual(len(groups), len(expected_groups))
        for key, value in groups.iteritems():
            self.assertTrue(key in expected_groups)
            expected = expected_groups[key]
            self.assertEqual(value.name, expected.name)
            for block in value.blocks:
                self.assertTrue(block in expected.blocks)

    def test_xml_to_groups_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        groups = OrderedDict()
        blocks = OrderedDict()
        root_xml = ElementTree.fromstring(strip_out_namespace(GROUPS_XML))

        # act
        xc.groups_from_xml(root_xml, groups, blocks)
        expected_groups = make_groups()

        # assert
        self.assertEqual(len(groups), len(expected_groups))
        for key, value in groups.iteritems():
            self.assertTrue(key in expected_groups)
            expected = expected_groups[key]
            self.assertEqual(value.name, expected.name)
            for block in value.blocks:
                self.assertTrue(block in expected.blocks)

    def test_xml_to_iocs_converts_correctly(self):
        # arrange
        xc = self.xml_converter
        iocs = OrderedDict()
        root_xml = ElementTree.fromstring(strip_out_namespace(IOCS_XML))

        # act
        xc.ioc_from_xml(root_xml, iocs)
        expected_iocs = make_iocs()

        # assert
        self.assertEqual(len(iocs), len(expected_iocs))
        for n, ioc in iocs.iteritems():
            self.assertTrue(n in expected_iocs)

            self.assertEqual(ioc.autostart, True)
            self.assertEqual(ioc.restart, False)

            self.assertEqual(len(ioc.macros), 1)
            self.assertEqual(len(ioc.pvs), 1)
            self.assertEqual(len(ioc.pvsets), 1)

            for mn, v in ioc.macros.iteritems():
                self.assertEqual(mn, n + "MACRO")
                self.assertTrue(v > 0)
            for pn, v in ioc.pvs.iteritems():
                self.assertEqual(pn, n + "PV")
                self.assertTrue(v > 0)
            for pn, v in ioc.pvsets.iteritems():
                self.assertEqual(pn, n + "PVSET")
                self.assertTrue(v)

    def test_xml_to_meta_converts_correctly(self):
        #arrange
        xc = self.xml_converter
        root_xml = ElementTree.fromstring(META_XML)
        meta = MetaData('Test')

        #act
        xc.meta_from_xml(root_xml, meta)
        expected_meta = make_meta()

        #assert
        self.assertEqual(meta.name, expected_meta.name)
        self.assertEqual(meta.description, expected_meta.description)
        self.assertEqual(meta.history, expected_meta.history)