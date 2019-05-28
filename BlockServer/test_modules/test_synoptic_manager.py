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


from BlockServer.synoptic.synoptic_manager import SynopticManager, SYNOPTIC_PRE, SYNOPTIC_GET
from BlockServer.core.config_list_manager import InvalidDeleteException
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.synoptic.synoptic_file_io import SynopticFileIO

TEST_DIR = os.path.abspath(".")

EXAMPLE_SYNOPTIC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                      <instrument xmlns="http://www.isis.stfc.ac.uk//instrument">
                      <name>%s</name>
                      </instrument>"""

SCHEMA_FOLDER = "schema"

SYNOPTIC_1 = "synop1"
SYNOPTIC_2 = "synop2"


def construct_pv_name(name):
    return SYNOPTIC_PRE + name + SYNOPTIC_GET


class MockSynopticFileIO(SynopticFileIO):
    def __init__(self):
        # Store the synoptics in memory
        self.syns = dict()

    def write_synoptic_file(self, name, save_path, xml_data):
        self.syns[name.lower() + ".xml"] = xml_data

    def read_synoptic_file(self, directory, fullname):
        return self.syns[fullname.lower()]

    def get_list_synoptic_files(self, directory):
        return self.syns.keys()

    def delete_synoptic(self, directory, fullname):
        del self.syns[fullname]


class TestSynopticManagerSequence(unittest.TestCase):
    def setUp(self):
        # Find the schema directory
        dir = os.path.join(".")
        while SCHEMA_FOLDER not in os.listdir(dir):
            dir = os.path.join(dir, "..")

        self.dir = dir

        self.fileIO = MockSynopticFileIO()
        self.bs = MockBlockServer()
        self.sm = SynopticManager(self.bs, os.path.join(self.dir, SCHEMA_FOLDER), None, self.fileIO)

    def _create_a_synoptic(self, name, sm):
        sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % name)

    def test_get_synoptic_names_returns_names_alphabetically(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        self._create_a_synoptic(SYNOPTIC_2, self.sm)

        # Act
        s = self.sm.get_synoptic_list()

        # Assert
        self.assertTrue(len(s) > 0)
        n = [x['name'] for x in s]
        self.assertEqual("-- NONE --", n[0])
        self.assertEqual(SYNOPTIC_1, n[1])
        self.assertEqual(SYNOPTIC_2, n[2])

    def test_create_pvs_is_okay(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        # Act
        self.sm._load_initial()

        # Assert
        self.assertTrue(self.bs.does_pv_exist("%sSYNOP1%s" % (SYNOPTIC_PRE, SYNOPTIC_GET)))

    def test_get_default_synoptic_xml_returns_nothing(self):
        # Arrange
        # Act
        xml = self.sm.get_default_synoptic_xml()

        # Assert
        self.assertEqual(xml, "")

    def test_set_default_synoptic_xml_sets_something(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        # Act
        self.sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % "synoptic0")
        self.sm.set_default_synoptic("synoptic0")

        # Assert
        xml = self.sm.get_default_synoptic_xml()

        self.assertTrue(len(xml) > 0)
        # Check the correct name appears in the xml
        self.assertTrue("synoptic0" in xml)

    def test_set_current_synoptic_xml_creates_pv(self):
        # Arrange
        syn_name = "synopt"

        # Act
        self.sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % syn_name)

        # Assert
        self.assertTrue(self.bs.does_pv_exist("%sSYNOPT%s" % (SYNOPTIC_PRE, SYNOPTIC_GET)))

    def test_delete_synoptics_empty(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        self._create_a_synoptic(SYNOPTIC_2, self.sm)
        initial_len = len(self.sm.get_synoptic_list())
        # Act
        self.sm.delete([])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), initial_len)
        self.assertTrue(SYNOPTIC_1 in synoptic_names)
        self.assertTrue(SYNOPTIC_2 in synoptic_names)
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_delete_one_synoptic(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        self._create_a_synoptic(SYNOPTIC_2, self.sm)
        initial_len = len(self.sm.get_synoptic_list())

        # Act
        self.sm.delete([SYNOPTIC_1])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), initial_len - 1)
        self.assertFalse(SYNOPTIC_1 in synoptic_names)
        self.assertTrue(SYNOPTIC_2 in synoptic_names)
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_delete_many_synoptics(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        self._create_a_synoptic(SYNOPTIC_2, self.sm)
        initial_len = len(self.sm.get_synoptic_list())
        # Act
        self.sm.delete([SYNOPTIC_1, SYNOPTIC_2])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), initial_len - 2)
        self.assertFalse(SYNOPTIC_1 in synoptic_names)
        self.assertFalse(SYNOPTIC_2 in synoptic_names)
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_cannot_delete_non_existent_synoptic(self):
        # Arrange
        self._create_a_synoptic(SYNOPTIC_1, self.sm)
        self._create_a_synoptic(SYNOPTIC_2, self.sm)
        initial_len = len(self.sm.get_synoptic_list())
        # Act
        self.assertRaises(InvalidDeleteException, self.sm.delete, ["invalid"])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), initial_len)
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))
