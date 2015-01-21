from config.file_event_handler import ConfigFileEventHandler
from config_server import ConfigServerManager
from mocks.mock_watcher_manager import MockWatcherManager
import config.constants as const
import unittest
import os
import shutil
import json

TEST_DIRECTORY = os.path.abspath(".\\test_configs")
SCHEMA_DIR = os.path.abspath("..\\..\\..\\schema\\configurations")

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

class TestFileEventHandler(unittest.TestCase):

    def setUp(self):
        os.makedirs(os.path.abspath(TEST_DIRECTORY))
        self.fw = MockWatcherManager()
        self.eh = ConfigFileEventHandler(self.fw, SCHEMA_DIR, None, False, test_mode=True)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + '\\'):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + '\\'))

    def test_schema_valid_xml(self):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        configserver.save_config(json.dumps("TESTCONFIG"))

        for xml in const.VALID_FILENAMES:
            self.eh._check_files_correct(TEST_DIRECTORY + '\\TEST_CONFIG\\' + xml)

            self.assertEqual(self.fw.get_error_message(), "")
            self.assertEqual(self.fw.get_warning_messages(), [])

    def test_schema_add_invalid_xml(self):
        new_file = TEST_DIRECTORY + '\\' + const.FILENAME_IOCS
        with open(new_file, 'w') as f:
            f.write("Invalid xml")

        self.eh._check_files_correct(new_file)

        self.assertNotEqual(self.fw.get_error_message(), "")
        self.assertEqual(self.fw.get_warning_messages(), [])

    def test_creating_invalid_files(self):
        new_file = TEST_DIRECTORY + '\\TEST_FILE.xml'
        with open(new_file, 'w') as f:
            f.write("This file is not part of a configuration")

        self.eh._check_files_correct(new_file)

        self.assertEqual(self.fw.get_error_message(), "")
        self.assertEqual(len(self.fw.get_warning_messages()), 1)
        self.assertEqual(self.fw.get_warning_messages(), ["Non-Config file found"])