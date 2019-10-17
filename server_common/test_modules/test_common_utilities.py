import unittest
from server_common.utilities import create_pv_name, remove_from_end, lowercase_and_make_unique


class TestCreatePVName(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_WHEN_pv_name_contains_whitespace_THEN_replace_whitespace_with_underscore(self):
        # Act
        pv = create_pv_name("config name", [], "PEEVEE")

        # Assert
        self.assertEquals(pv, "CONFIG")

    def test_WHEN_pv_name_contains_non_alphanumeric_characters_THEN_remove_non_alphanumeric_characters(self):
        # Act
        pv = create_pv_name("c-onf@ig", [], "PEEVEE")

        # Assert
        self.assertEquals(pv, "CONFIG")

    def test_WHEN_pv_name_contains_only_numbers_and_underscores_THEN_replace_pv_with_default_pv_name(self):
        # Act
        pv = create_pv_name("1_2_3_4", [], "PEEVEE")

        # Assert
        self.assertEquals(pv, "PEEVEE")

    def test_WHEN_pv_name_is_blank_THEN_replace_pv_with_default_pv_name(self):
        # Act
        pv = create_pv_name("", [], "PEEVEE")

        # Assert
        self.assertEquals(pv, "PEEVEE")

    def test_GIVEN_blank_pv_name_WHEN_another_blank_pv_name_THEN_append_numbers(self):
        # Arrange
        pv_01 = create_pv_name("", [], "PEEVEE")

        # Act
        pv_02 = create_pv_name("", [pv_01], "PEEVEE")
        pv_03 = create_pv_name("", [pv_01, pv_02], "PEEVEE")

        # Assert
        self.assertEquals(pv_01, "PEEVEE")
        self.assertEquals(pv_02, "PEEV01")
        self.assertEquals(pv_03, "PEEV02")

    def test_WHEN_pv_name_too_long_THEN_truncate_to_six_chars(self):
        # Act
        pv = create_pv_name("Configuration", [], "PEEVEE")

        # Assert
        self.assertEquals(pv, "CONFIG")

    def test_GIVEN_an_existing_pv_WHEN_create_another_pv_of_same_name_THEN_append_numbers(self):
        # Arrange
        pv_01 = create_pv_name("Conf", [], "PEEVEE")

        # Act
        pv_02 = create_pv_name("Conf", [pv_01], "PEEVEE")

        # Assert
        self.assertEquals(pv_01, "CONF")
        self.assertEquals(pv_02, "CONF01")

    def test_GIVEN_an_existing_truncated_pv_WHEN_another_pv_of_same_name_THEN_truncate_and_rename_differently(self):
        # Arrange
        pv_01 = create_pv_name("Configuration", [], "PEEVEE")

        # Act
        pv_02 = create_pv_name("Configuration", [pv_01], "PEEVEE")
        pv_03 = create_pv_name("Configuration", [pv_01, pv_02], "PEEVEE")

        # Assert
        self.assertEquals(pv_01, "CONFIG")
        self.assertEquals(pv_02, "CONF01")
        self.assertEquals(pv_03, "CONF02")

    def test_GIVEN_a_long_pv_WHEN_create_pv_with_same_name_and_invalid_chars_THEN_remove_invalid_chars_and_truncate_and_number_correctly(self):
        # Arrange
        pv_01 = create_pv_name("Configuration", [], "PEEVEE")

        # Act
        pv_02 = create_pv_name("Co*&^nfiguration", [pv_01], "PEEVEE")

        # Assert
        self.assertEquals(pv_01, "CONFIG")
        self.assertEquals(pv_02, "CONF01")

    def test_GIVEN_pv_name_contains_a_colon_WHEN_colons_not_allowed_THEN_colons_removed(self):
        # Act
        pv = create_pv_name("BL:AH:BL:", [], "PEEVEE", allow_colon=False)

        # Assert
        self.assertEquals(pv, "BLAHBL")

    def test_GIVEN_pv_name_contains_a_colon_WHEN_colons_allowed_THEN_colons_retained(self):
        # Act
        pv = create_pv_name("BL:AH:BL:", [], "PEEVEE", allow_colon=True)

        # Assert
        self.assertEquals(pv, "BL:AH:BL"[:6])

    def test_WHEN_string_contains_ending_THEN_ending_removed(self):
        # Arrange
        ending = "END"
        text = "text"

        # Act
        result = remove_from_end(text + ending, ending)

        # Assert
        self.assertEquals(text, result)

    def test_WHEN_string_does_not_contains_ending_THEN_text_returned(self):
        # Arrange
        ending = "END"
        text = "text"

        # Act
        result = remove_from_end(text, ending)

        # Assert
        self.assertEquals(text, result)

    def test_WHEN_string_is_empty_THEN_empty_text_returned(self):
        # Arrange
        ending = "END"
        text = ""

        # Act
        result = remove_from_end(text, ending)

        # Assert
        self.assertEquals(text, result)

    def test_WHEN_string_is_None_THEN_None_returned(self):
        # Arrange
        ending = "END"
        text = None

        # Act
        result = remove_from_end(text, ending)

        # Assert
        self.assertIsNone(result)


class TestMakeUniqueAndLowercase(unittest.TestCase):
    def test_WHEN_called_with_empty_list_THEN_result_is_empty(self):
        self.assertEqual(0, len(lowercase_and_make_unique([])))

    def test_WHEN_called_with_duplicates_THEN_duplicates_are_removed(self):
        self.assertEqual(1, len(lowercase_and_make_unique(["a", "a"])))

    def test_WHEN_called_without_duplicates_THEN_nothing_removed(self):
        self.assertEqual(2, len(lowercase_and_make_unique(["a", "b"])))

    def test_WHEN_called_with_uppercase_strings_THEN_strings_made_lowercase(self):
        result = lowercase_and_make_unique(["A", "B"])
        self.assertIn("a", result)
        self.assertIn("b", result)

    def test_WHEN_called_with_same_string_in_both_upper_and_lower_case_THEN_only_lowercase_version_kept(self):
        result = lowercase_and_make_unique(["a", "A"])
        self.assertEqual(1, len(result))
        self.assertIn("a", result)
