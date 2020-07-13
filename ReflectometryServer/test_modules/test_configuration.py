import os
import unittest

from ReflectometryServer import beamline_configuration, ConfigHelper
from ReflectometryServer.server_status_manager import STATUS, _ServerStatusManager
import ReflectometryServer.server_status_manager
from ReflectometryServer.test_modules.test_config.good_config.refl.config import OPTIONAL_PARAM_1
from ReflectometryServer.test_modules.test_config.good_config.refl.other_config import OTHER_CONFIG_PARAM


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        ReflectometryServer.beamline.STATUS_MANAGER = _ServerStatusManager()
        ConfigHelper.reset()

    def test_WHEN_loading_valid_beamline_configuration_file_THEN_correct_PVs_are_created(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({})
        #  Check Status PV
        self.assertEqual(STATUS.OKAY, ReflectometryServer.beamline.STATUS_MANAGER.status)

    def test_WHEN_loading_invalid_beamline_configuration_file_THEN_status_PV_shows_error(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "error_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({})
        #  Check Status PV
        self.assertEqual(STATUS.ERROR, ReflectometryServer.server_status_manager.STATUS_MANAGER.status)

    def test_WHEN_loading_beamline_configuration_file_that_doesnt_exist_THEN_status_PV_shows_import_error(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({})
        #  Check Status PV
        self.assertEqual(STATUS.ERROR, ReflectometryServer.server_status_manager.STATUS_MANAGER.status)

    def test_GIVEN_valid_other_config_file_in_macro_WHEN_loading_config_THEN_other_config_is_loaded(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({"CONFIG_FILE": "other_config.py"})
        #  Check Status PV
        self.assertEqual(STATUS.OKAY, ReflectometryServer.beamline.STATUS_MANAGER.status)
        self.assertTrue(OTHER_CONFIG_PARAM in beamline.parameters.keys())

    def test_GIVEN_optional_macro_set_WHEN_loading_config_THEN_optional_items_part_of_config(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({"OPTIONAL_1": True})
        #  Check Status PV
        self.assertEqual(STATUS.OKAY, ReflectometryServer.beamline.STATUS_MANAGER.status)
        self.assertTrue(OPTIONAL_PARAM_1 in beamline.parameters.keys())

    def test_GIVEN_optional_macro_not_set_WHEN_loading_config_THEN_optional_items_not_part_of_config(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration({"OPTIONAL_1": False})
        #  Check Status PV
        self.assertEqual(STATUS.OKAY, ReflectometryServer.beamline.STATUS_MANAGER.status)
        self.assertTrue(OPTIONAL_PARAM_1 not in beamline.parameters.keys())
