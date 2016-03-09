'''
This file is part of the ISIS IBEX application.
Copyright (C) 2012-2015 Science & Technology Facilities Council.
All rights reserved.

This program is distributed in the hope that it will be useful.
This program and the accompanying materials are made available under the
terms of the Eclipse Public License v1.0 which accompanies this distribution.
EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.

You should have received a copy of the Eclipse Public License v1.0
along with this program; if not, you can obtain a copy from
https://www.eclipse.org/org/documents/epl-v10.php or 
http://opensource.org/licenses/eclipse-1.0.php
'''
import unittest
import os
import json
import shutil

from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema, NotConfigFileException
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.constants import SCHEMA_FOR, FILENAME_IOCS
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_runcontrol_manager import MockRunControlManager
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.file_path_manager import FILEPATH_MANAGER

TEST_DIRECTORY = os.path.abspath("test_configs")
SCHEMA_DIR = os.path.abspath(os.path.join("..", "schema"))

TEST_CONFIG = {"iocs":
                 [{"simlevel": "devsim", "autostart": True, "restart": False,
                 "macros": [{"name": "COMPORT", "value": "COM[0-9]+"}],
                 "pvsets": [{"name": "SET", "enabled": "true"}],
                 "pvs": [{"name": "NDWXXX:xxxx:SIMPLE:VALUE1", "value": "100"}],
                 "name": "SIMPLE1", "component": None},

                  {"simlevel": "recsim", "autostart": False, "restart": True,
                  "macros": [],
                  "pvsets": [],
                  "pvs": [],
                  "name": "SIMPLE2", "component": None}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": True,
                   "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                    {"name": "testblock2", "local": True,
                    "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                    {"name": "testblock3", "local": True,
                    "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "component": None, "visible": True,
                        "runcontrol": False,
                        "log_periodic": False, "log_rate": 5, "log_deadband": 0}
                   ],
          "components":
                       [{"name": "TEST_COMP"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "component": None},
                    {"blocks": ["testblock2"], "name": "Group2", "component": None},
                    {"blocks": ["testblock3"], "name": "NONE", "component": None}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration",
          "synoptic": "TEST_SYNOPTIC",
		  "history": ["2015-02-16"]
         }


def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY)
        self.cs = ActiveConfigHolder(MACROS, ArchiverManager(None, None, MockArchiverWrapper()),
                                     MockVersionControl(), MockIocControl(""), MockRunControlManager())

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_schema_valid_xml_empty_config(self):
        self.cs.save_active("TEST_CONFIG")

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_config_file_matches_schema(SCHEMA_DIR,
                                                                          os.path.join(FILEPATH_MANAGER.config_dir,
                                                                                       'TEST_CONFIG', xml)))

    def test_schema_valid_xml_full_config(self):
        self.cs.save_active("TEST_COMP", as_comp=True)
        self.cs.set_config_details(TEST_CONFIG)
        self.cs.save_active("TEST_CONFIG")

        for xml in SCHEMA_FOR:
            self.assertTrue(ConfigurationSchemaChecker.check_config_file_matches_schema(SCHEMA_DIR,
                                                                         os.path.join(FILEPATH_MANAGER.config_dir,
                                                                                      'TEST_CONFIG', xml)))

    def test_schema_invalid_xml(self):
        os.makedirs(os.path.join(FILEPATH_MANAGER.config_dir, 'TEST_CONFIG') + os.sep)
        new_file = os.path.join(FILEPATH_MANAGER.config_dir, 'TEST_CONFIG', FILENAME_IOCS)
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_config_file_matches_schema,
                          SCHEMA_DIR, new_file)

    def test_schema_invalid_file(self):
        new_file = os.path.join(FILEPATH_MANAGER.config_dir, 'TEST_FILE.xml')
        with open(new_file, 'w') as f:
            f.write("This file is not part of a configuration")

        self.assertRaises(NotConfigFileException, ConfigurationSchemaChecker.check_config_file_matches_schema,
                          SCHEMA_DIR, new_file)

    def test_schema_whole_directory_valid(self):
        self.cs.save_active("TEST_CONFIG")
        self.cs.save_active("TEST_COMP", as_comp=True)

        self.assertTrue(ConfigurationSchemaChecker.check_all_config_files_correct(SCHEMA_DIR, TEST_DIRECTORY))

    def test_schema_whole_directory_invalid(self):
        os.makedirs(os.path.join(FILEPATH_MANAGER.component_dir, 'TEST_COMP') + os.sep)
        new_file = os.path.join(FILEPATH_MANAGER.component_dir, 'TEST_COMP', FILENAME_IOCS)
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.assertRaises(ConfigurationInvalidUnderSchema, ConfigurationSchemaChecker.check_all_config_files_correct,
                          SCHEMA_DIR, TEST_DIRECTORY)
