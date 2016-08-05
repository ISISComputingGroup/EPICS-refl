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
# Along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import os
import re
import unittest
from xml.etree import ElementTree
from collections import OrderedDict

from BlockServer.config.configuration import Configuration
from BlockServer.config.group import Group
from BlockServer.config.block import Block
from BlockServer.config.ioc import IOC
from BlockServer.config.metadata import MetaData
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.core.macros import MACROS


BLOCKS_XML = u"""
<?xml version="1.0" ?>
<blocks xmlns="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:blk="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
    <block>
        <name>TESTBLOCK1</name>
        <read_pv>TESTPV1</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_enabled>True</rc_enabled>
        <rc_lowlimit>1</rc_lowlimit>
        <rc_highlimit>2</rc_highlimit>
        <log_periodic>False</log_periodic>
        <log_rate>5</log_rate>
        <log_deadband>0</log_deadband>
    </block>
    <block>
        <name>TESTBLOCK2</name>
        <read_pv>TESTPV2</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_enabled>True</rc_enabled>
        <rc_lowlimit>1</rc_lowlimit>
        <rc_highlimit>2</rc_highlimit>
        <log_periodic>False</log_periodic>
        <log_rate>5</log_rate>
        <log_deadband>0</log_deadband>
    </block>
    <block>
        <name>TESTBLOCK3</name>
        <read_pv>TESTPV3</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_enabled>True</rc_enabled>
        <rc_lowlimit>1</rc_lowlimit>
        <rc_highlimit>2</rc_highlimit>
        <log_periodic>False</log_periodic>
        <log_rate>5</log_rate>
        <log_deadband>0</log_deadband>
    </block>
    <block>
        <name>TESTBLOCK4</name>
        <read_pv>TESTPV4</read_pv>
        <local>True</local>
        <visible>True</visible>
        <rc_enabled>True</rc_enabled>
        <rc_lowlimit>1</rc_lowlimit>
        <rc_highlimit>2</rc_highlimit>
        <log_periodic>False</log_periodic>
        <log_rate>5</log_rate>
        <log_deadband>0</log_deadband>
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
            <macro name="TESTIOC2MACRO" value="1"/>
            <macro name="TESTIOC1MACRO" value="1"/>
        </macros>
        <pvs>
            <pv name="TESTIOC1PV" value="1"/>
            <pv name="TESTIOC2PV" value="1"/>
        </pvs>
        <pvsets>
            <pvset enabled="True" name="TESTIOC2PVSET"/>
            <pvset enabled="True" name="TESTIOC1PVSET"/>
        </pvsets>
    </ioc>
    <ioc autostart="true" name="TESTIOC2" restart="false" simlevel="devsim">
        <macros>
            <macro name="TESTIOC2MACRO" value="2"/>
            <macro name="TESTIOC1MACRO" value="2"/>
        </macros>
        <pvs>
            <pv name="TESTIOC1PV" value="2"/>
            <pv name="TESTIOC2PV" value="2"/>
        </pvs>
        <pvsets>
            <pvset enabled="True" name="TESTIOC2PVSET"/>
            <pvset enabled="True" name="TESTIOC1PVSET"/>
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

COMP_XML = u"""<?xml version="1.0" ?>
<components xmlns="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:comp="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
<component name="comp1"/>
<component name="comp2"/>
</components>"""


def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


def strip_out_namespace(string):
    return re.sub(' xmlns="[^"]+"', '', string, count=1)

BLOCKS_XML = strip_out_whitespace(BLOCKS_XML)
GROUPS_XML = strip_out_whitespace(GROUPS_XML)
IOCS_XML = strip_out_whitespace(IOCS_XML)


def make_blocks():
    blocks = OrderedDict()
    for i in range(1, 5):
        num = str(i)
        new_block_args = ["TESTBLOCK" + num, "TESTPV" + num, True, True, False, True, 1, 2]
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
        iocs["TESTIOC" + str(i)].macros["TESTIOC1MACRO"] = {"value": i}
        iocs["TESTIOC" + str(i)].macros["TESTIOC2MACRO"] = {"value": i}
        iocs["TESTIOC" + str(i)].pvs["TESTIOC1PV"] = {"value": i}
        iocs["TESTIOC" + str(i)].pvs["TESTIOC2PV"] = {"value": i}
        iocs["TESTIOC" + str(i)].pvsets["TESTIOC1PVSET"] = {"enabled": True}
        iocs["TESTIOC" + str(i)].pvsets["TESTIOC2PVSET"] = {"enabled": True}
    return iocs


def make_meta():
    meta = MetaData('Test', description='A test description', synoptic="TEST_SYNOPTIC")
    meta.history = ["1992-02-07"]
    return meta


def make_comps():
    config = Configuration(None)
    config.components["comp1"] = "comp1"
    config.components["comp2"] = "comp2"
    return config.components


class TestConfigurationXmlConverterSequence(unittest.TestCase):
    def setUp(self):
        # Create a new XML converter
        self.xml_converter = ConfigurationXmlConverter()

    def tearDown(self):
        pass

    def test_blocks_to_xml_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        blocks = make_blocks()

        # Act
        blocks_xml = xc.blocks_to_xml(blocks, MACROS)
        blocks_xml = strip_out_whitespace(blocks_xml)

        # Assert
        self.assertEqual(blocks_xml, BLOCKS_XML)

    def test_groups_to_xml_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        groups = make_groups()

        # Act
        groups_xml = xc.groups_to_xml(groups)
        groups_xml = strip_out_whitespace(groups_xml)

        # Assert
        self.assertEqual(groups_xml, GROUPS_XML)

    def test_iocs_to_xml_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        iocs = make_iocs()

        # Act
        iocs_xml = xc.iocs_to_xml(iocs)
        iocs_xml = strip_out_whitespace(iocs_xml)

        # Assert
        self.maxDiff = None
        self.assertEqual(iocs_xml.strip(), IOCS_XML.strip())

    def test_meta_to_xml_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        meta = make_meta()

        # Act
        meta_xml = xc.meta_to_xml(meta)
        meta_xml = strip_out_whitespace(meta_xml)

        # Assert
        self.assertEqual(meta_xml.strip(), META_XML.strip())

    def test_comps_to_xml_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        comps = make_comps()

        # Act
        comp_xml = xc.components_to_xml(comps)
        comp_xml = strip_out_whitespace(comp_xml)

        # Assert
        self.assertEqual(comp_xml.strip(), COMP_XML.strip())

    def test_xml_to_blocks_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        blocks = OrderedDict()
        groups = {"none": Group("NONE")}
        root_xml = ElementTree.fromstring(BLOCKS_XML)

        # Act
        xc.blocks_from_xml(root_xml, blocks, groups)
        expected_blocks = make_blocks()

        # Assert
        self.assertEqual(len(blocks), len(expected_blocks))
        for key, value in blocks.iteritems():
            self.assertTrue(key in expected_blocks)
            expected = expected_blocks[key]
            self.assertEqual(value.name, expected.name)
            self.assertEqual(value.pv, expected.pv)
            self.assertEqual(value.local, expected.local)
            self.assertEqual(value.rc_enabled, expected.rc_enabled)
            self.assertEqual(value.rc_lowlimit, expected.rc_lowlimit)
            self.assertEqual(value.rc_highlimit, expected.rc_highlimit)
            self.assertEqual(value.log_periodic, expected.log_periodic)
            self.assertEqual(value.log_rate, expected.log_rate)
            self.assertEqual(value.log_deadband, expected.log_deadband)

    def test_xml_to_comps_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        comps = OrderedDict()
        root_xml = ElementTree.fromstring(COMP_XML)

        # Act
        xc.components_from_xml(root_xml, comps)

        # Assert
        self.assertTrue("comp1" in comps)
        self.assertTrue("comp1" in comps)

    def test_xml_to_groups_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        groups = OrderedDict()
        blocks = OrderedDict()
        root_xml = ElementTree.fromstring(GROUPS_XML)

        # Act
        xc.groups_from_xml(root_xml, groups, blocks)
        expected_groups = make_groups()

        # Assert
        self.assertEqual(len(groups), len(expected_groups))
        for key, value in expected_groups.iteritems():
            self.assertTrue(key in groups)
            grp = groups[key]
            self.assertEqual(value.name, grp.name)
            for block in value.blocks:
                self.assertTrue(block in grp.blocks)

    def test_xml_to_iocs_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        iocs = OrderedDict()
        root_xml = ElementTree.fromstring(IOCS_XML)

        # Act
        xc.ioc_from_xml(root_xml, iocs)
        expected_iocs = make_iocs()

        # Assert
        self.assertEqual(len(iocs), len(expected_iocs))
        for n, ioc in iocs.iteritems():
            self.assertTrue(n in expected_iocs)

            self.assertEqual(ioc.autostart, True)
            self.assertEqual(ioc.restart, False)

            self.assertEqual(len(ioc.macros), 2)
            self.assertTrue("TESTIOC1MACRO" in ioc.macros)
            self.assertTrue("TESTIOC2MACRO" in ioc.macros)

            self.assertEqual(len(ioc.pvs), 2)
            self.assertTrue("TESTIOC1PV" in ioc.pvs)
            self.assertTrue("TESTIOC2PV" in ioc.pvs)

            self.assertEqual(len(ioc.pvsets), 2)
            self.assertTrue("TESTIOC1PVSET" in ioc.pvsets)
            self.assertTrue("TESTIOC2PVSET" in ioc.pvsets)

    def test_xml_to_component_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        comps = OrderedDict()
        root_xml = ElementTree.fromstring(COMP_XML)

        # Act
        xc.components_from_xml(root_xml, comps)

        # Assert
        self.assertEqual(len(comps), 2)
        self.assertTrue("comp1" in comps)
        self.assertTrue("comp2" in comps)

    def test_xml_to_meta_converts_correctly(self):
        # Arrange
        xc = self.xml_converter
        root_xml = ElementTree.fromstring(META_XML)
        meta = MetaData('Test')

        # Act
        xc.meta_from_xml(root_xml, meta)
        expected_meta = make_meta()

        # Assert
        self.assertEqual(meta.name, expected_meta.name)
        self.assertEqual(meta.description, expected_meta.description)
        self.assertEqual(meta.history, expected_meta.history)

    def test_xml_to_blocks_converts_correctly_with_no_namespace(self):
        # Arrange
        xc = self.xml_converter
        blocks = OrderedDict()
        groups = {"none": Group("NONE")}
        root_xml = ElementTree.fromstring(strip_out_namespace(BLOCKS_XML))

        # Act
        xc.blocks_from_xml(root_xml, blocks, groups)
        expected_blocks = make_blocks()

        # Assert
        self.assertEqual(len(blocks), len(expected_blocks))
        for key, value in blocks.iteritems():
            self.assertTrue(key in expected_blocks)
            expected = expected_blocks[key]
            self.assertEqual(value.name, expected.name)
            self.assertEqual(value.pv, expected.pv)
            self.assertEqual(value.local, expected.local)
            self.assertEqual(value.rc_enabled, expected.rc_enabled)
            self.assertEqual(value.rc_lowlimit, expected.rc_lowlimit)
            self.assertEqual(value.rc_highlimit, expected.rc_highlimit)
            self.assertEqual(value.log_periodic, expected.log_periodic)
            self.assertEqual(value.log_rate, expected.log_rate)
            self.assertEqual(value.log_deadband, expected.log_deadband)

    def test_xml_to_iocs_converts_correctly_with_no_namespace(self):
        # Arrange
        xc = self.xml_converter
        iocs = OrderedDict()
        root_xml = ElementTree.fromstring(strip_out_namespace(IOCS_XML))

        # Act
        xc.ioc_from_xml(root_xml, iocs)
        expected_iocs = make_iocs()

        # Assert
        self.assertEqual(len(iocs), len(expected_iocs))
        for n, ioc in iocs.iteritems():
            self.assertTrue(n in expected_iocs)

            self.assertEqual(ioc.autostart, True)
            self.assertEqual(ioc.restart, False)

            self.assertEqual(len(ioc.macros), 2)
            self.assertTrue("TESTIOC1MACRO" in ioc.macros)
            self.assertTrue("TESTIOC2MACRO" in ioc.macros)

            self.assertEqual(len(ioc.pvs), 2)
            self.assertTrue("TESTIOC1PV" in ioc.pvs)
            self.assertTrue("TESTIOC2PV" in ioc.pvs)

            self.assertEqual(len(ioc.pvsets), 2)
            self.assertTrue("TESTIOC1PVSET" in ioc.pvsets)
            self.assertTrue("TESTIOC2PVSET" in ioc.pvsets)

    def test_xml_to_groups_converts_correctly_with_no_namespace(self):
        # Arrange
        xc = self.xml_converter
        groups = OrderedDict()
        blocks = OrderedDict()
        root_xml = ElementTree.fromstring(strip_out_namespace(GROUPS_XML))

        # Act
        xc.groups_from_xml(root_xml, groups, blocks)
        expected_groups = make_groups()

        # Assert
        self.assertEqual(len(groups), len(expected_groups))
        for key, value in groups.iteritems():
            self.assertTrue(key in expected_groups)
            expected = expected_groups[key]
            self.assertEqual(value.name, expected.name)
            for block in value.blocks:
                self.assertTrue(block in expected.blocks)

    def test_xml_to_component_converts_correctly_with_no_namespace(self):
        # Arrange
        xc = self.xml_converter
        comps = OrderedDict()
        root_xml = ElementTree.fromstring(strip_out_namespace(COMP_XML))

        # Act
        xc.components_from_xml(root_xml, comps)

        # Assert
        self.assertEqual(len(comps), 2)
        self.assertTrue("comp1" in comps)
        self.assertTrue("comp2" in comps)

    def test_roundtrip_block_to_xml_to_block(self):
        # Arrange
        xc = self.xml_converter
        blocks = OrderedDict()
        groups = {"none": Group("NONE")}
        initial_blocks = make_blocks()

        # Act
        blocks_xml = xc.blocks_to_xml(initial_blocks, MACROS)
        root_xml = ElementTree.fromstring(blocks_xml)
        xc.blocks_from_xml(root_xml, blocks, groups)

        # Assert
        self.assertEqual(len(blocks), len(initial_blocks))
        for key, value in blocks.iteritems():
            self.assertTrue(key in initial_blocks)
            expected = initial_blocks[key]
            self.assertEqual(value.name, expected.name)
            self.assertEqual(value.pv, expected.pv)
            self.assertEqual(value.local, expected.local)
            self.assertEqual(value.rc_enabled, expected.rc_enabled)
            self.assertEqual(value.rc_lowlimit, expected.rc_lowlimit)
            self.assertEqual(value.rc_highlimit, expected.rc_highlimit)
            self.assertEqual(value.log_periodic, expected.log_periodic)
            self.assertEqual(value.log_rate, expected.log_rate)
            self.assertEqual(value.log_deadband, expected.log_deadband)

    def test_roundtrip_group_to_xml_to_group(self):
        # Arrange
        xc = self.xml_converter
        groups = OrderedDict()
        blocks = OrderedDict()
        initial_groups = make_groups()

        # Act
        groups_xml = xc.groups_to_xml(initial_groups)
        root_xml = ElementTree.fromstring(groups_xml)
        xc.groups_from_xml(root_xml, groups, blocks)

        # Assert
        self.assertEqual(len(groups), len(initial_groups))
        for key, value in groups.iteritems():
            self.assertTrue(key in initial_groups)
            expected = initial_groups[key]
            self.assertEqual(value.name, expected.name)
            for block in value.blocks:
                self.assertTrue(block in expected.blocks)

    def test_roundtrip_iocs_to_xml_to_iocs(self):
        # Arrange
        xc = self.xml_converter
        iocs = OrderedDict()
        initial_iocs = make_iocs()

        # Act
        iocs_xml = xc.iocs_to_xml(initial_iocs)
        root_xml = ElementTree.fromstring(iocs_xml)
        xc.ioc_from_xml(root_xml, iocs)

        # Assert
        self.assertEqual(len(iocs), len(initial_iocs))
        for n, ioc in iocs.iteritems():
            self.assertTrue(n in initial_iocs)

            self.assertEqual(ioc.autostart, True)
            self.assertEqual(ioc.restart, False)

            self.assertEqual(len(ioc.macros), 2)
            self.assertEqual(len(ioc.pvs), 2)
            self.assertEqual(len(ioc.pvsets), 2)

    def test_roundtrip_meta_to_xml_to_meta(self):
        # Arrange
        xc = self.xml_converter
        initial_meta = make_meta()

        # Act
        meta_xml = xc.meta_to_xml(initial_meta)
        root_xml = ElementTree.fromstring(meta_xml)
        meta = MetaData('Test')
        xc.meta_from_xml(root_xml, meta)

        # Assert
        self.assertEqual(meta.name, initial_meta.name)
        self.assertEqual(meta.description, initial_meta.description)
        self.assertEqual(meta.history, initial_meta.history)

    def test_roundtrip_comps_to_xml_to_comps(self):
        # Arrange
        xc = self.xml_converter
        initial_comps = make_comps()

        # Act
        comp_xml = xc.components_to_xml(initial_comps)
        root_xml = ElementTree.fromstring(comp_xml)
        comps = OrderedDict()
        xc.components_from_xml(root_xml, comps)

        # Assert
        self.assertEqual(len(comps), 2)
        self.assertTrue("comp1" in comps)
        self.assertTrue("comp2" in comps)