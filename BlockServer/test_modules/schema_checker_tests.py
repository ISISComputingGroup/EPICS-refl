import unittest
import os
import json
import shutil
from config.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema, NotConfigFileException
from config_server import ConfigServerManager
from config.constants import SCHEMA_FOR, FILENAME_IOCS, CONFIG_DIRECTORY, COMPONENT_DIRECTORY
from macros import MACROS

TEST_DIRECTORY = os.path.abspath(".\\test_configs")
CONFIG_DIR = TEST_DIRECTORY + CONFIG_DIRECTORY
SUBCONFIG_DIR = TEST_DIRECTORY + COMPONENT_DIRECTORY
SCHEMA_DIR = os.path.abspath("..\\..\\..\\schema\\configurations")


class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        os.makedirs(CONFIG_DIR)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + '\\'):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + '\\'))

    def test_schema_valid_xml(self):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        configserver.save_config(json.dumps("TEST_CONFIG"))

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_config_file_correct(SCHEMA_DIR,
                                                                          CONFIG_DIR + '\\TEST_CONFIG\\' + xml))

    def test_schema_invalid_xml(self):
        os.makedirs(CONFIG_DIR + 'TEST_CONFIG\\')
        new_file = CONFIG_DIR + 'TEST_CONFIG\\' + FILENAME_IOCS
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_config_file_correct,
                          SCHEMA_DIR, new_file)

    def test_schema_invalid_file(self):
        new_file = CONFIG_DIR + '\\TEST_FILE.xml'
        with open(new_file, 'w') as f:
            f.write("This file is not part of a configuration")

        self.assertRaises(NotConfigFileException, ConfigurationSchemaChecker.check_config_file_correct, SCHEMA_DIR,
                          new_file)

    def test_schema_whole_directory_valid(self):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        configserver.save_config(json.dumps("TEST_CONFIG"))
        configserver.save_as_subconfig(json.dumps("TEST_SUBCONFIG"))

        self.assertTrue(ConfigurationSchemaChecker.check_all_config_files_correct(SCHEMA_DIR, TEST_DIRECTORY))

    def test_schema_whole_directory_invalid(self):
        os.makedirs(SUBCONFIG_DIR + 'TEST_COMP\\')
        new_file = SUBCONFIG_DIR + 'TEST_COMP\\' + FILENAME_IOCS
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_all_config_files_correct,
                          SCHEMA_DIR, TEST_DIRECTORY)