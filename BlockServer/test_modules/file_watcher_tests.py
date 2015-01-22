from config.file_watcher_manager import ConfigFileWatcherManager
import config.constants as const
import unittest
import os
import shutil
import time

TEST_DIRECTORY = os.path.abspath(".\\test_configs")
SCHEMA_DIR = os.path.abspath("..\\..\\..\\schema\\configurations")

CONFIG_DIR = TEST_DIRECTORY + const.CONFIG_DIRECTORY
COMPONENT_DIR = TEST_DIRECTORY + const.COMPONENT_DIRECTORY

class TestFileWatcherManager(unittest.TestCase):
    # Test case is not completely comprehensive as must wait for file watcher, causing tests to take a long time

    def setUp(self):
        os.makedirs(CONFIG_DIR)
        os.makedirs(COMPONENT_DIR)
        self.fw = ConfigFileWatcherManager(TEST_DIRECTORY, SCHEMA_DIR, True)

    def tearDown(self):
        self.fw.pause()
        self.fw.pause(True)
        if os.path.isdir(TEST_DIRECTORY + '\\'):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + '\\'))

    def test_creating_folders_not_event(self):
        os.makedirs(CONFIG_DIR + '\\TEST_CONFIG\\')

        time.sleep(1.5)

        self.assertFalse(self.fw.config_fired())
        self.assertFalse(self.fw.subconfig_fired())

    def test_catches_config_file_events(self):
        test_conf_folder = CONFIG_DIR + '\\TEST_CONFIG'
        os.makedirs(test_conf_folder)
        with open(test_conf_folder + '/config.xml', 'w') as f:
            f.write('TEST FILE')

        time.sleep(1.5)

        self.assertTrue(self.fw.config_fired())
        self.assertFalse(self.fw.subconfig_fired())