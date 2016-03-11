import unittest
import os
from BlockServer.core.file_path_manager import FILEPATH_MANAGER, CONFIG_DIRECTORY, COMPONENT_DIRECTORY, \
    SYNOPTIC_DIRECTORY


class TestFilePathManagerSequence(unittest.TestCase):
    def setUp(self):
        self.path = os.path.abspath(os.getcwd())
        FILEPATH_MANAGER.initialise(self.path)

    def test_config_root_dir_correct(self):
        self.assertEqual(self.path, FILEPATH_MANAGER.config_root_dir)

    def test_config_dir_correct(self):
        self.assertEqual(os.path.join(self.path, CONFIG_DIRECTORY), FILEPATH_MANAGER.config_dir)

    def test_component_dir_correct(self):
        self.assertEqual(os.path.join(self.path, COMPONENT_DIRECTORY), FILEPATH_MANAGER.component_dir)

    def test_synoptic_dir_correct(self):
        self.assertEqual(os.path.join(self.path, SYNOPTIC_DIRECTORY), FILEPATH_MANAGER.synoptic_dir)

    def test_config_folder_path_correct(self):
        config = "test"
        self.assertEqual(os.path.join(self.path, CONFIG_DIRECTORY, config) + os.sep,
                         FILEPATH_MANAGER.get_config_path(config))

    def test_component_folder_path_correct(self):
        component = "test"
        self.assertEqual(os.path.join(self.path, COMPONENT_DIRECTORY, component) + os.sep,
                         FILEPATH_MANAGER.get_component_path(component))

    def test_synoptic_file_path_correct(self):
        synoptic = "test"
        self.assertEqual(os.path.join(self.path, SYNOPTIC_DIRECTORY, synoptic) + ".xml",
                         FILEPATH_MANAGER.get_synoptic_path(synoptic))