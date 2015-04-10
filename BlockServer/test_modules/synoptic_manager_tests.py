import unittest
import os
import shutil

from BlockServer.core.synoptic_manager import SynopticManager, SYNOPTIC_PRE, SYNOPTIC_GET
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.core.constants import SYNOPTIC_DIRECTORY


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

    def test_get_synoptic_filenames_from_nonexistant_directory_returns_empty_list(self):
        # Arrange
        sm = SynopticManager("K:\\I_DONT_EXIST\\", MockCAServer(), SCHEMA_PATH)

        # Act
        s = sm.get_synoptic_filenames()

        # Assert
        self.assertEqual(len(s), 0)

    def test_get_synoptic_filenames_from_directory_returns_names(self):
        # Arrange
        sm = SynopticManager(TEST_DIR, MockCAServer(), SCHEMA_PATH)

        # Act
        s = sm.get_synoptic_filenames()

        # Assert
        self.assertTrue(len(s) > 0)
        self.assertTrue("synoptic1.xml" in s)
        self.assertTrue("synoptic2.xml" in s)

    def test_create_pvs_is_okay(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(TEST_DIR, cas, SCHEMA_PATH)

        # Act
        sm.create_pvs()

        # Assert
        self.assertTrue(len(cas.pv_list) > 0)
        self.assertTrue("%sSYNOPTIC1%s" % (SYNOPTIC_PRE, SYNOPTIC_GET) in cas.pv_list.keys())

    def test_get_current_synoptic_xml_returns_something(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(TEST_DIR, cas, SCHEMA_PATH)

        # Act
        xml = sm.get_default_synoptic_xml()

        # Assert
        self.assertTrue(len(xml) > 0)

    def test_set_current_synoptic_xml_sets_something(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(TEST_DIR, cas, SCHEMA_PATH)

        # Act
        sm.set_synoptic_xml(EXAMPLE_SYNOPTIC % "synoptic0")

        # Assert
        xml = sm.get_default_synoptic_xml()
        self.assertTrue(len(xml) > 0)

    def test_set_current_synoptic_xml_saves_under_name(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(TEST_DIR, cas, SCHEMA_PATH)
        SYN_NAME = "new_synoptic"

        # Act
        sm.set_synoptic_xml(EXAMPLE_SYNOPTIC % SYN_NAME)

        # Assert
        synoptics = sm.get_synoptic_filenames()
        self.assertTrue(SYN_NAME in [f[0:-4] for f in synoptics])

    def test_set_current_synoptic_xml_creates_pv(self):
        # Arrange
        cas = MockCAServer()
        sm = SynopticManager(TEST_DIR, cas, SCHEMA_PATH)
        SYN_NAME = "new_synoptic"

        # Act
        sm.set_synoptic_xml(EXAMPLE_SYNOPTIC % SYN_NAME)

        # Assert
        self.assertTrue(len(cas.pv_list) > 0)
        self.assertTrue("%sNEW_SYNOPTIC%s" % (SYNOPTIC_PRE, SYNOPTIC_GET) in cas.pv_list.keys())