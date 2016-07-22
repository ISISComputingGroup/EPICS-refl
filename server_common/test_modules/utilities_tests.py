import unittest
from server_common.utilities import create_pv_name


class TestCreatePVName(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_when_config_name_contains_whitespace_then_replace_with_underscore(self):
        pass

    def test_when_config_name_contains_non_alphanumeric_characters_then_remove(self):
        pass

    def test_when_config_name_contains_only_numbers_and_underscores_then_replace_with_default_config_name(self):
        pass

    def test_when_config_name_is_blank_then_replace_with_default_config_name(self):
        create_pv_name("", [], "Default")
        self.assertEquals(create_pv_name(), "Default")

    def test_given_blank_config_name_when_another_blank_config_name_then_append_numbers(self):
        pass