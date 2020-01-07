from __future__ import unicode_literals, absolute_import, print_function, division
import unittest
import shutil
import os

from server_common.autosave import AutosaveFile


TEMP_FOLDER = os.path.join("C:\\", "instrument", "var", "tmp", "autosave_tests")


class TestAutosave(unittest.TestCase):
    def setUp(self):
        self.autosave = AutosaveFile(service_name="unittests", file_name="test_file", folder=TEMP_FOLDER)
        try:
            os.makedirs(TEMP_FOLDER)
        except:
            pass

    def test_GIVEN_no_existing_file_WHEN_get_parameter_from_autosave_THEN_default_returned(self):
        default = object()
        self.assertEqual(self.autosave.read_parameter("some_random_parameter", default), default)

    def test_GIVEN_parameter_saved_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(self):
        value = "test_value"
        self.autosave.write_parameter("parameter", value)
        self.assertEqual(self.autosave.read_parameter("parameter", None), value)

    def test_GIVEN_different_parameter_saved_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(self):
        value = "test_value"
        self.autosave.write_parameter("other_parameter", value)
        self.assertEqual(self.autosave.read_parameter("parameter", None), None)

    def test_GIVEN_parameter_saved_with_different_strategy_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(self):

        class Strategy:
            @staticmethod
            def autosave_convert_for_write(values):
                return ",".join([str(value) for value in values])

            @staticmethod
            def autosave_convert_for_read(auto_save_value):
                return [int(i) for i in auto_save_value.split(",")]

        autosave = AutosaveFile(service_name="unittests", file_name="strat_test_file", folder=TEMP_FOLDER, conversion=Strategy())
        value = [1, 2]
        autosave.write_parameter("parameter_ab", value)
        self.assertEqual(autosave.read_parameter("parameter_ab", None), value)

    def tearDown(self):
        try:
            shutil.rmtree(TEMP_FOLDER)
        except:
            pass
