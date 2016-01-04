import unittest
import os
import json
import shutil

from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema, NotConfigFileException
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.constants import SCHEMA_FOR, FILENAME_IOCS, CONFIG_DIRECTORY, COMPONENT_DIRECTORY
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_runcontrol_manager import MockRunControlManager
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager

TEST_DIRECTORY = os.path.abspath("test_configs")
CONFIG_DIR = os.path.join(TEST_DIRECTORY, CONFIG_DIRECTORY)
SUBCONFIG_DIR = os.path.join(TEST_DIRECTORY, COMPONENT_DIRECTORY)
SCHEMA_DIR = os.path.abspath(os.path.join("..","..","..","..","schema","configurations"))

TEST_CONFIG = {"iocs":
                 [{"simlevel": "devsim", "autostart": True, "restart": False,
                 "macros": [{"name": "COMPORT", "value": "COM[0-9]+"}],
                 "pvsets": [{"name": "SET", "enabled": "true"}],
                 "pvs": [{"name": "NDWXXX:xxxx:SIMPLE:VALUE1", "value": "100"}],
                 "name": "SIMPLE1", "subconfig": None},

                  {"simlevel": "recsim", "autostart": False, "restart": True,
                  "macros": [],
                  "pvsets": [],
                  "pvs": [],
                  "name": "SIMPLE2", "subconfig": None}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": True,
                   "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": None, "visible": True},
                    {"name": "testblock2", "local": True,
                    "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": None, "visible": True},
                    {"name": "testblock3", "local": True,
                    "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": None, "visible": True,
                        "runcontrol": False,
                        "log_periodic": False, "log_rate": 5, "log_deadband": 0}
                   ],
          "components":
                       [{"name": "TEST_SUB"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": None},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": None},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": None}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration",
          "synoptic": "TEST_SYNOPTIC",
		  "history": ["2015-02-16"]
         }


def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        os.makedirs(CONFIG_DIR)
        self.cs = ActiveConfigHolder(TEST_DIRECTORY, MACROS, ArchiverManager(None, None, MockArchiverWrapper()),
                                     MockVersionControl(), MockIocControl(""), MockRunControlManager())

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_schema_valid_xml_empty_config(self):
        self.cs.save_active("TEST_CONFIG")

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_config_file_matches_schema(SCHEMA_DIR,
                                                                          os.path.join(CONFIG_DIR, 'TEST_CONFIG', xml)))

    def test_schema_valid_xml_full_config(self):
        self.cs.save_active("TEST_SUB", as_comp=True)
        self.cs.set_config_details(TEST_CONFIG)
        self.cs.save_active("TEST_CONFIG")

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_config_file_matches_schema(SCHEMA_DIR,
                                                                         os.path.join(CONFIG_DIR, 'TEST_CONFIG', xml)))

    def test_schema_invalid_xml(self):
        os.makedirs(os.path.join(CONFIG_DIR, 'TEST_CONFIG') + os.sep)
        new_file = os.path.join(CONFIG_DIR, 'TEST_CONFIG', FILENAME_IOCS)
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_config_file_matches_schema,
                          SCHEMA_DIR, new_file)

    def test_schema_invalid_file(self):
        new_file = os.path.join(CONFIG_DIR, 'TEST_FILE.xml')
        with open(new_file, 'w') as f:
            f.write("This file is not part of a configuration")

        self.assertRaises(NotConfigFileException, ConfigurationSchemaChecker.check_config_file_matches_schema,
                          SCHEMA_DIR, new_file)

    def test_schema_whole_directory_valid(self):
        self.cs.save_active("TEST_CONFIG")
        self.cs.save_active("TEST_SUBCONFIG", as_comp=True)

        self.assertTrue(ConfigurationSchemaChecker.check_all_config_files_correct(SCHEMA_DIR, TEST_DIRECTORY))

    def test_schema_whole_directory_invalid(self):
        os.makedirs(os.path.join(SUBCONFIG_DIR, 'TEST_COMP') + os.sep)
        new_file = os.path.join(SUBCONFIG_DIR, 'TEST_COMP', FILENAME_IOCS)
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_all_config_files_correct,
                          SCHEMA_DIR, TEST_DIRECTORY)
