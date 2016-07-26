import unittest
from server_common.utilities import create_pv_name


class TestCreatePVName(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_when_config_name_contains_whitespace_then_replace_with_underscore(self):
        config = create_pv_name("config name", [], "Default")

        self.assertEquals(config, "CONFIG_NAME")
        pass

    def test_when_config_name_contains_non_alphanumeric_characters_then_remove(self):
        config = create_pv_name("c-onf@ig *n>ame=!", [], "Default")

        self.assertEquals(config, "CONFIG_NAME")
        pass

    def test_when_config_name_contains_only_numbers_and_underscores_then_replace_with_default_config_name(self):
        config = create_pv_name("1_2_3_4", [], "Default")

        self.assertEquals(config, "Default")
        pass

    def test_when_config_name_is_blank_then_replace_with_default_config_name(self):
        config = create_pv_name("", [], "Default")

        self.assertEquals(config, "Default")

    def test_given_blank_config_name_when_another_blank_config_name_then_append_numbers(self):
        config_01 = create_pv_name("", [], "Default")
        config_02 = create_pv_name("", [config_01], "Default")
        config_03 = create_pv_name("", [config_01, config_02], "Default")

        self.assertEquals(config_01, "Default")
        self.assertEquals(config_02, "Default0")
        self.assertEquals(config_03, "Default1")