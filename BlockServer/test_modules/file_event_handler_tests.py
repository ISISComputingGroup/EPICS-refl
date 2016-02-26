from threading import RLock
import unittest
import os
import shutil

from BlockServer.core.config_list_manager import ConfigListManager
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.fileIO.config_file_event_handler import ConfigFileEventHandler
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


TEST_DIRECTORY = os.path.abspath("test_configs")
SCHEMA_DIR = os.path.abspath(os.path.join("..","..","..","..","schema","configurations"))

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}


class TestFileEventHandler(unittest.TestCase):

    def setUp(self):
        FILEPATH_MANAGER.initialise(TEST_DIRECTORY)
        self.config_list = ConfigListManager(MockBlockServer, MockCAServer(), SCHEMA_DIR,
                                             MockVersionControl())
        self.eh = ConfigFileEventHandler(SCHEMA_DIR, RLock(), self.config_list, False)

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_get_config_name_valid_structure(self):
        config_folder = 'TEST_CONFIG'
        name = self.eh._get_config_name(os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml'))

        self.assertEqual(name, config_folder)

    def test_get_config_name_valid_nested_structure(self):
        config_folder = 'TEST_CONFIG'
        name = self.eh._get_config_name(os.path.join(FILEPATH_MANAGER.config_dir, config_folder, 'TEST_FILE.xml'))

        self.assertEqual(name, config_folder)

    def test_file_not_in_correct_place(self):
        self.assertFalse(self.eh._check_file_at_root(os.path.join(FILEPATH_MANAGER.config_root_dir, 'TEST_FILE.xml')))
