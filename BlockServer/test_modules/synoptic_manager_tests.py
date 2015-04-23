import unittest
import os
import shutil

from BlockServer.core.synoptic_manager import SynopticManager, SYNOPTIC_PRE, SYNOPTIC_GET
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.core.constants import SYNOPTIC_DIRECTORY
from BlockServer.core.config_list_manager import InvalidDeleteException
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_block_server import MockBlockServer

TEST_DIR = os.path.abspath(".\\" + SYNOPTIC_DIRECTORY)

EXAMPLE_SYNOPTIC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                      <instrument xmlns="http://www.isis.stfc.ac.uk//instrument">
                      <name>%s</name>
                      </instrument>"""

SCHEMA_PATH = "./../../../schema/configurations"

class TestSynopticManagerSequence(unittest.TestCase):
    def setUp(self):
        # Make directory and fill with fake synoptics
        if not os.path.isdir(TEST_DIR + '\\'):
            os.makedirs(TEST_DIR)

        f1 = open(TEST_DIR + "\\synoptic1.xml", "a")
        f1.write(EXAMPLE_SYNOPTIC % "synoptic1")
        f1.close()
        f2 = open(TEST_DIR + "\\synoptic2.xml", "a")
        f2.write(EXAMPLE_SYNOPTIC % "synoptic2")
        f2.close()

    def tearDown(self):
        # Delete test directory
        shutil.rmtree(TEST_DIR)

    def test_get_synoptic_filenames_from_directory_returns_names(self):
        # Arrange
        sm = SynopticManager(MockBlockServer(), TEST_DIR, MockCAServer(), SCHEMA_PATH, MockVersionControl())

        # Act
        s = sm.get_synoptic_list()

        # Assert
        self.assertTrue(len(s) > 0)
        s = [x['name'] for x in s]
        self.assertTrue("synoptic1" in s)
        self.assertTrue("synoptic2" in s)

    def test_create_pvs_is_okay(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm._load_initial()

        # Assert
        self.assertTrue(len(cas.pv_list) > 0)
        self.assertTrue("%sSYNOPTIC1%s" % (SYNOPTIC_PRE, SYNOPTIC_GET) in cas.pv_list.keys())

    def test_get_current_synoptic_xml_returns_something(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        xml = sm.get_default_synoptic_xml()

        # Assert
        self.assertTrue(len(xml) > 0)

    def test_set_current_synoptic_xml_sets_something(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % "synoptic0")

        # Assert
        xml = sm.get_default_synoptic_xml()
        self.assertTrue(len(xml) > 0)

    def test_set_current_synoptic_xml_saves_under_name(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())
        SYN_NAME = "new_synoptic"

        # Act
        sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % SYN_NAME)

        # Assert
        synoptics = sm._get_synoptic_filenames()
        self.assertTrue(SYN_NAME + ".xml" in synoptics)

    def test_set_current_synoptic_xml_creates_pv(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())
        SYN_NAME = "new_synoptic"

        # Act
        sm.save_synoptic_xml(EXAMPLE_SYNOPTIC % SYN_NAME)

        # Assert
        self.assertTrue(len(cas.pv_list) > 0)
        self.assertTrue("%sNEW_SYNOPTIC%s" % (SYNOPTIC_PRE, SYNOPTIC_GET) in cas.pv_list.keys())

    def test_delete_synoptics_empty(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm.delete_synoptics([])

        # Assert
        synoptic_names = [c["name"] for c in sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), 2)
        self.assertTrue("synoptic1" in synoptic_names)
        self.assertTrue("synoptic2" in synoptic_names)
        self.assertEqual(len(cas.pv_list), 2)

    def test_delete_one_config(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm.delete_synoptics(["synoptic1"])

        # Assert
        synoptic_names = [c["name"] for c in sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), 1)
        self.assertFalse("synoptic1" in synoptic_names)
        self.assertTrue("synoptic2" in synoptic_names)
        self.assertEqual(len(cas.pv_list), 1)

    def test_delete_many_configs(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm.delete_synoptics(["synoptic1", "synoptic2"])

        # Assert
        synoptic_names = [c["name"] for c in sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), 0)
        self.assertFalse("synoptic1" in synoptic_names)
        self.assertFalse("synoptic2" in synoptic_names)
        self.assertEqual(len(cas.pv_list), 0)

    def test_delete_config_affects_filesystem(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        sm.delete_synoptics(["synoptic1"])

        # Assert
        synoptics = os.listdir(TEST_DIR)
        self.assertEqual(len(synoptics), 1)
        self.assertTrue("synoptic2.xml" in synoptics)

    def test_cant_delete_non_existant_synoptic(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(MockBlockServer(), TEST_DIR, cas, SCHEMA_PATH, MockVersionControl())

        # Act
        self.assertRaises(InvalidDeleteException, sm.delete_synoptics, ["invalid"])

        # Assert
        synoptic_names = [c["name"] for c in sm.get_synoptic_list()]
        self.assertEqual(len(synoptic_names), 2)
        self.assertEqual(len(cas.pv_list), 2)