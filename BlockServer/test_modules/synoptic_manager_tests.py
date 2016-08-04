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
import shutil


from BlockServer.synoptic.synoptic_manager import SynopticManager, SYNOPTIC_PRE, SYNOPTIC_GET
from BlockServer.core.config_list_manager import InvalidDeleteException
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.core.file_path_manager import FILEPATH_MANAGER

TEST_DIR = os.path.abspath(".")

EXAMPLE_SYNOPTIC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                      <instrument xmlns="http://www.isis.stfc.ac.uk//instrument">
                      <name>%s</name>
                      </instrument>"""

SCHEMA_PATH = os.path.abspath(os.path.join(".", "..", "schema"))

SYNOPTIC_1 = "synop1"
SYNOPTIC_2 = "synop2"


def construct_pv_name(name):
    return SYNOPTIC_PRE + name + SYNOPTIC_GET


class TestSynopticManagerSequence(unittest.TestCase):
    def setUp(self):
        # Make directory and fill with fake synoptics
        if not os.path.isdir(FILEPATH_MANAGER.synoptic_dir):
            os.makedirs(FILEPATH_MANAGER.synoptic_dir)

        f1 = open(os.path.join(FILEPATH_MANAGER.synoptic_dir, SYNOPTIC_1 + ".xml"), "a")
        f1.write(EXAMPLE_SYNOPTIC % SYNOPTIC_1)
        f1.close()
        f2 = open(os.path.join(FILEPATH_MANAGER.synoptic_dir, SYNOPTIC_2 + ".xml"), "a")
        f2.write(EXAMPLE_SYNOPTIC % SYNOPTIC_2)
        f2.close()

        self.bs = MockBlockServer()
        self.sm = SynopticManager(self.bs, SCHEMA_PATH, MockVersionControl(), None)
        self.initial_len = len([c["name"] for c in self.sm.get_synoptic_list()])

    def tearDown(self):
        # Delete test directory
        shutil.rmtree(FILEPATH_MANAGER.synoptic_dir)

    def test_get_synoptic_filenames_from_directory_returns_names_alphabetically(self):
        # Arrange
        # Act
        s = self.sm.get_synoptic_list()

        # Assert
        self.assertTrue(len(s) > 0)
        s = [x['name'] for x in s]
        self.assertTrue(s[0], SYNOPTIC_1)
        self.assertTrue(s[0], SYNOPTIC_2)

    def test_create_pvs_is_okay(self):
        # Arrange
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
        # Act
        self.sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % "synoptic0")
        self.sm.set_default_synoptic("synoptic0")

        # Assert
        xml = self.sm.get_default_synoptic_xml()

        self.assertTrue(len(xml) > 0)
        # Check the correct name appears in the xml
        self.assertTrue("synoptic0" in xml)

    def test_set_current_synoptic_xml_saves_under_name(self):
        # Arrange
        syn_name = "new_synoptic"

        # Act
        self.sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % syn_name)

        # Assert
        synoptics = self.sm._get_synoptic_filenames()
        self.assertTrue(syn_name + ".xml" in synoptics)

    def test_set_current_synoptic_xml_creates_pv(self):
        # Arrange
        syn_name = "synopt"

        # Act
        self.sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % syn_name)

        # Assert
        self.assertTrue(self.bs.does_pv_exist("%sSYNOPT%s" % (SYNOPTIC_PRE, SYNOPTIC_GET)))

    def test_delete_synoptics_empty(self):
        # Arrange
        # Act
        self.sm.delete_synoptics([])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), self.initial_len)
        self.assertTrue(SYNOPTIC_1 in synoptic_names)
        self.assertTrue(SYNOPTIC_2 in synoptic_names)
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_delete_one_config(self):
        # Arrange
        # Act
        self.sm.delete_synoptics([SYNOPTIC_1])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), self.initial_len - 1)
        self.assertFalse(SYNOPTIC_1 in synoptic_names)
        self.assertTrue(SYNOPTIC_2 in synoptic_names)
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_delete_many_configs(self):
        # Arrange
        # Act
        self.sm.delete_synoptics([SYNOPTIC_1, SYNOPTIC_2])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), self.initial_len - 2)
        self.assertFalse(SYNOPTIC_1 in synoptic_names)
        self.assertFalse(SYNOPTIC_2 in synoptic_names)
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertFalse(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))

    def test_delete_config_affects_filesystem(self):
        # Arrange
        # Act
        self.sm.delete_synoptics([SYNOPTIC_1])

        # Assert
        synoptics = os.listdir(FILEPATH_MANAGER.synoptic_dir)
        self.assertEqual(len(synoptics), 1)
        self.assertTrue("synop2.xml" in synoptics)

    def test_cannot_delete_non_existent_synoptic(self):
        # Arrange
        # Act
        self.assertRaises(InvalidDeleteException, self.sm.delete_synoptics, ["invalid"])

        # Assert
        synoptic_names = [c["name"] for c in self.sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), self.initial_len)
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_1.upper())))
        self.assertTrue(self.bs.does_pv_exist(construct_pv_name(SYNOPTIC_2.upper())))
