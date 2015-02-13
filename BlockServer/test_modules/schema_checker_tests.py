import unittest
import os
import json
import shutil

from config.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema, NotConfigFileException
from active_config_server import ActiveConfigServerManager
from config.constants import SCHEMA_FOR, FILENAME_IOCS, CONFIG_DIRECTORY, COMPONENT_DIRECTORY
from macros import MACROS

TEST_DIRECTORY = os.path.abspath(".\\test_configs")
CONFIG_DIR = TEST_DIRECTORY + CONFIG_DIRECTORY
SUBCONFIG_DIR = TEST_DIRECTORY + COMPONENT_DIRECTORY
SCHEMA_DIR = os.path.abspath("..\\..\\..\\schema\\configurations")

TEST_JSON = """{"iocs":
                 [{"simlevel": "devsim", "autostart": true, "restart": false,
                 "macros": [{"name": "COMPORT", "value": "COM[0-9]+"}],
                 "pvsets": [{"name": "SET", "enabled": "true"}],
                 "pvs": [{"name": "NDWXXX:xxxx:SIMPLE:VALUE1", "value": "100"}],
                 "name": "SIMPLE1", "subconfig": null},

                  {"simlevel": "recsim", "autostart": false, "restart": true,
                  "macros": [],
                  "pvsets": [],
                  "pvs": [],
                  "name": "SIMPLE2", "subconfig": null}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": true,
                   "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock2", "local": true,
                    "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock3", "local": true,
                    "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
                   ],
          "components":
                       [{"name": "TEST_SUB"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration"
         }"""


def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        os.makedirs(CONFIG_DIR)
        self.cs = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:", test_mode=True)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + '\\'):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + '\\'))

    def test_schema_valid_xml_empty_config(self):
        self.cs.save_config(json.dumps("TEST_CONFIG"))

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_matches_schema(SCHEMA_DIR,
                                                                          CONFIG_DIR + '\\TEST_CONFIG\\' + xml))

    def test_schema_valid_xml_full_config(self):
        test_json = strip_out_whitespace(TEST_JSON)
        self.cs.save_as_subconfig(json.dumps("TEST_SUB"))
        self.cs.set_config_details(test_json)
        self.cs.save_config(json.dumps("TEST_CONFIG"))

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_matches_schema(SCHEMA_DIR,
                                                                          CONFIG_DIR + '\\TEST_CONFIG\\' + xml))

    def test_schema_invalid_xml(self):
        os.makedirs(CONFIG_DIR + 'TEST_CONFIG\\')
        new_file = CONFIG_DIR + 'TEST_CONFIG\\' + FILENAME_IOCS
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_matches_schema,
                          SCHEMA_DIR, new_file)

    def test_schema_invalid_file(self):
        new_file = CONFIG_DIR + '\\TEST_FILE.xml'
        with open(new_file, 'w') as f:
            f.write("This file is not part of a configuration")

        self.assertRaises(NotConfigFileException, ConfigurationSchemaChecker.check_matches_schema, SCHEMA_DIR,
                          new_file)

    def test_schema_whole_directory_valid(self):
        self.cs.save_config(json.dumps("TEST_CONFIG"))
        self.cs.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))

        self.assertTrue(ConfigurationSchemaChecker.check_all_config_files_correct(SCHEMA_DIR, TEST_DIRECTORY))

    def test_schema_whole_directory_invalid(self):
        os.makedirs(SUBCONFIG_DIR + 'TEST_COMP\\')
        new_file = SUBCONFIG_DIR + 'TEST_COMP\\' + FILENAME_IOCS
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_all_config_files_correct,
                          SCHEMA_DIR, TEST_DIRECTORY)