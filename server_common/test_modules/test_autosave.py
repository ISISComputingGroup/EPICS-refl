from __future__ import unicode_literals, absolute_import, print_function, division
import unittest
import shutil
import os

from hamcrest import *
from parameterized import parameterized

from server_common.autosave import AutosaveFile, FloatConversion, BoolConversion

TEMP_FOLDER = os.path.join("C:\\", "instrument", "var", "tmp", "autosave_tests")


class TestAutosave(unittest.TestCase):
    def setUp(self):

        try:
            os.makedirs(TEMP_FOLDER)
        except:
            pass
        self.autosave = AutosaveFile(service_name="unittests", file_name="test_file", folder=TEMP_FOLDER)

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

    def test_GIVEN_parameter_saved_as_float_WHEN_get_parameter_from_autosave_THEN_value_returned_as_float(self):
        value = 0.173
        key = "parameter"
        autosave = AutosaveFile(service_name="unittests",
                                file_name="test_file", folder=TEMP_FOLDER, conversion=FloatConversion())

        autosave.write_parameter(key, value)
        result = autosave.read_parameter(key, None)

        assert_that(result, is_(value))

    def test_GIVEN_parameter_can_not_be_saved_as_float_WHEN_get_parameter_from_autosave_THEN_none_returned(self):
        value = "string not a float"
        key = "parameter"
        autosave = AutosaveFile(service_name="unittests",
                                file_name="test_file", folder=TEMP_FOLDER, conversion=FloatConversion())

        autosave.write_parameter(key, value)
        result = autosave.read_parameter(key, None)

        assert_that(result, is_(None))

    @parameterized.expand([(True,), (False,)])
    def test_GIVEN_true_saved_as_bool_WHEN_get_parameter_from_autosave_THEN_value_returned_as_ture(self, value):
        key = "parameter"
        autosave = AutosaveFile(service_name="unittests",
                                file_name="test_file", folder=TEMP_FOLDER, conversion=BoolConversion())

        autosave.write_parameter(key, value)
        result = autosave.read_parameter(key, None)

        assert_that(result, is_(value))

    def test_GIVEN_parameter_can_not_be_saved_as_bool_WHEN_get_parameter_from_autosave_THEN_none_returned(self):
        value = "string not a bool"
        key = "parameter"
        autosave = AutosaveFile(service_name="unittests",
                                file_name="test_file", folder=TEMP_FOLDER, conversion=BoolConversion())

        autosave.write_parameter(key, value)
        result = autosave.read_parameter(key, None)

        assert_that(result, is_(None))

    def tearDown(self):
        try:
            shutil.rmtree(TEMP_FOLDER)
        except:
            pass
