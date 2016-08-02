import unittest
from server_common.utilities import create_pv_name


class TestCreatePVName(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_when_pv_name_contains_whitespace_then_replace_with_underscore(self):
        pv = create_pv_name("config name", [], "peevee")

        self.assertEquals(pv, "CONFIG")

    def test_when_pv_name_contains_non_alphanumeric_characters_then_remove(self):
        pv = create_pv_name("c-onf@ig", [], "peevee")

        self.assertEquals(pv, "CONFIG")

    def test_when_pv_name_contains_only_numbers_and_underscores_then_replace_with_default_pv_name(self):
        pv = create_pv_name("1_2_3_4", [], "peevee")

        self.assertEquals(pv, "peevee")

    def test_when_pv_name_is_blank_then_replace_with_default_pv_name(self):
        pv = create_pv_name("", [], "peevee")

        self.assertEquals(pv, "peevee")

    def test_given_blank_pv_name_when_another_blank_pv_name_then_append_numbers(self):
        pv_01 = create_pv_name("", [], "peevee")
        pv_02 = create_pv_name("", [pv_01], "peevee")
        pv_03 = create_pv_name("", [pv_01, pv_02], "peevee")

        self.assertEquals(pv_01, "peevee")
        self.assertEquals(pv_02, "peev01")
        self.assertEquals(pv_03, "peev02")

    def test_when_pv_name_too_long_then_truncate(self):
        pv = create_pv_name("Configuration", [], "peevee")

        self.assertEquals(pv, "CONFIG")

    def test_given_an_existing_pv_when_another_pv_of_same_name_then_rename_differently(self):
        pv_01 = create_pv_name("Conf", [], "peevee")
        pv_02 = create_pv_name("Conf", [pv_01], "peevee")

        self.assertEquals(pv_01, "CONF")
        self.assertEquals(pv_02, "CONF01")

    def test_given_an_existing_truncated_pv_when_another_pv_of_same_name_then_truncate_and_rename_differently(self):
        pv_01 = create_pv_name("Configuration", [], "peevee")
        pv_02 = create_pv_name("Configuration", [pv_01], "peevee")
        pv_03 = create_pv_name("Configuration", [pv_01, pv_02], "peevee")

        self.assertEquals(pv_01, "CONFIG")
        self.assertEquals(pv_02, "CONF01")
        self.assertEquals(pv_03, "CONF02")
