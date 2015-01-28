from all_configs_list import ConfigListManager
from server_common.mocks.mock_ca_server import MockCAServer
from mocks.mock_block_server import MockBlockServer
from config.file_event_handler import ConfigFileEventHandler, NotConfigFileException
from threading import RLock
import config.constants as const
import unittest
import os
import shutil


TEST_DIRECTORY = os.path.abspath(".\\test_configs")
CONFIG_DIR = TEST_DIRECTORY + const.CONFIG_DIRECTORY
SCHEMA_DIR = os.path.abspath("..\\..\\..\\schema\\configurations")

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}


class TestFileEventHandler(unittest.TestCase):

    def setUp(self):
        os.makedirs(CONFIG_DIR)
        self.config_list = ConfigListManager(MockBlockServer, TEST_DIRECTORY, MockCAServer(), True)
        self.eh = ConfigFileEventHandler(TEST_DIRECTORY, SCHEMA_DIR, RLock(), self.config_list, False, test_mode=True)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + '\\'):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + '\\'))

    def test_get_config_name_valid_structure(self):
        config_folder = 'TEST_CONFIG'

        print "Path is: " + CONFIG_DIR + config_folder + '\\TEST_FILE.xml'

        name = self.eh._get_config_name(CONFIG_DIR + config_folder + '\\TEST_FILE.xml')

        print "Config name is: " + str(name)

        self.assertEqual(name, config_folder)

    def test_get_config_name_valid_nested_structure(self):
        config_folder = 'TEST_CONFIG'
        name = self.eh._get_config_name(CONFIG_DIR + config_folder + '\\ANOTHER_FOLDER\\TEST_FILE.xml')

        self.assertEqual(name, config_folder)

    def test_get_config_name_invalid_structure(self):
        self.assertRaises(NotConfigFileException, self.eh._get_config_name, CONFIG_DIR + 'TEST_FILE.xml')