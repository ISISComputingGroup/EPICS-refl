import os
import unittest

from ReflectometryServer import beamline_configuration
from ReflectometryServer.server_status_manager import STATUS, _ServerStatusManager
import ReflectometryServer.server_status_manager


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        ReflectometryServer.beamline.STATUS_MANAGER = _ServerStatusManager()

    def test_WHEN_loading_valid_beamline_configuration_file_THEN_correct_PVs_are_created(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration()
        #  Check Status PV
        self.assertEqual(STATUS.OKAY, ReflectometryServer.beamline.STATUS_MANAGER.status)

    def test_WHEN_loading_invalid_beamline_configuration_file_THEN_status_PV_shows_error(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "error_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration()
        #  Check Status PV
        self.assertEqual(STATUS.ERROR, ReflectometryServer.server_status_manager.STATUS_MANAGER.status)

    def test_WHEN_loading_beamline_configuration_file_that_doesnt_exist_THEN_status_PV_shows_import_error(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "refl"))
        beamline = beamline_configuration.create_beamline_from_configuration()
        #  Check Status PV
        self.assertEqual(STATUS.ERROR, ReflectometryServer.server_status_manager.STATUS_MANAGER.status)
