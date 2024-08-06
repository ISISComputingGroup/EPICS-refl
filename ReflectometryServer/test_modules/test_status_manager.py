import unittest

from mock import Mock
from parameterized import parameterized
from pcaspy import Severity

from ReflectometryServer.server_status_manager import STATUS, ProblemInfo, _ServerStatusManager


class TestStatusManager(unittest.TestCase):
    def setUp(self):
        self.status_manager = _ServerStatusManager()
        self.status_manager._initialising = False

    def test_GIVEN_initial_state_WHEN_reading_server_status_THEN_status_is_okay(self):
        expected = STATUS.OKAY

        actual = self.status_manager.status

        self.assertEqual(expected, actual)

    def test_GIVEN_initial_state_WHEN_reading_server_problems_THEN_list_is_blank(self):
        expected = {}

        actual = self.status_manager.active_errors

        self.assertEqual(expected, actual)

    def test_GIVEN_major_severity_WHEN_new_problem_occurs_THEN_new_error_added_as_key_with_source_as_value(
        self,
    ):
        problem_description = "problem_description"
        source = Mock()
        problem_severity = Severity.MAJOR_ALARM
        problem = ProblemInfo(problem_description, source, problem_severity)
        expected = {problem_description: {source}}

        self.status_manager.update_active_problems(problem)
        actual = self.status_manager.active_errors

        self.assertEqual(expected, actual)
        self.assertEqual({}, self.status_manager.active_warnings)
        self.assertEqual({}, self.status_manager.active_other_problems)

    def test_GIVEN_minor_severity_WHEN_new_problem_occurs_THEN_new_warning_added_as_key_with_source_as_value(
        self,
    ):
        problem_description = "problem_description"
        source = Mock()
        problem_severity = Severity.MINOR_ALARM
        problem = ProblemInfo(problem_description, source, problem_severity)
        expected = {problem_description: {source}}

        self.status_manager.update_active_problems(problem)
        actual = self.status_manager.active_warnings

        self.assertEqual({}, self.status_manager.active_errors)
        self.assertEqual(expected, actual)
        self.assertEqual({}, self.status_manager.active_other_problems)

    def test_GIVEN_unknown_severity_WHEN_new_problem_occurs_THEN_new_other_problem_added_as_key_with_source_as_value(
        self,
    ):
        problem_description = "problem_description"
        source = Mock()
        problem_severity = None
        problem = ProblemInfo(problem_description, source, problem_severity)
        expected = {problem_description: {source}}

        self.status_manager.update_active_problems(problem)
        actual = self.status_manager.active_other_problems

        self.assertEqual({}, self.status_manager.active_errors)
        self.assertEqual({}, self.status_manager.active_warnings)
        self.assertEqual(expected, actual)

    def test_GIVEN_new_source_WHEN_known_problem_occurs_THEN_problem_entry_modified_by_adding_another_source(
        self,
    ):
        problem_description = "problem_description"
        source_1 = Mock()
        source_2 = Mock()
        problem_severity = Severity.MAJOR_ALARM
        expected = {problem_description: {source_1, source_2}}

        self.status_manager.update_active_problems(
            ProblemInfo(problem_description, source_1, problem_severity)
        )
        self.status_manager.update_active_problems(
            ProblemInfo(problem_description, source_2, problem_severity)
        )
        actual = self.status_manager.active_errors

        self.assertEqual(expected, actual)

    def test_GIVEN_known_source_WHEN_new_problem_occurs_THEN_new_problem_added_as_key_with_source_as_value(
        self,
    ):
        problem_description_1 = "problem_description_1"
        problem_description_2 = "problem_description_2"
        source = Mock()
        problem_severity = Severity.MAJOR_ALARM
        expected = {problem_description_1: {source}, problem_description_2: {source}}

        self.status_manager.update_active_problems(
            ProblemInfo(problem_description_1, source, problem_severity)
        )
        self.status_manager.update_active_problems(
            ProblemInfo(problem_description_2, source, problem_severity)
        )
        actual = self.status_manager.active_errors

        self.assertEqual(expected, actual)

    def test_GIVEN_known_source_WHEN_known_problem_occurs_THEN_problem_not_added_again(self):
        problem_description = "problem_description"
        source = Mock()
        problem_severity = Severity.MAJOR_ALARM
        problem = ProblemInfo(problem_description, source, problem_severity)
        expected = {problem_description: {source}}

        self.status_manager.update_active_problems(problem)
        self.status_manager.update_active_problems(problem)
        actual = self.status_manager.active_errors

        self.assertEqual(expected, actual)

    def test_GIVEN_non_empty_list_of_problems_WHEN_server_status_cleared_THEN_all_problems_are_cleared(
        self,
    ):
        source = Mock()
        problem_1 = ProblemInfo("problem_description_1", source, Severity.MAJOR_ALARM)
        problem_2 = ProblemInfo("problem_description_2", source, Severity.MINOR_ALARM)
        problem_3 = ProblemInfo("problem_description_2", source, Severity.INVALID_ALARM)
        self.status_manager.update_active_problems(problem_1)
        self.status_manager.update_active_problems(problem_2)
        self.status_manager.update_active_problems(problem_3)
        expected = {}

        self.status_manager.clear_all()

        self.assertEqual(expected, self.status_manager.active_errors)
        self.assertEqual(expected, self.status_manager.active_warnings)
        self.assertEqual(expected, self.status_manager.active_other_problems)

    @parameterized.expand(
        [
            (Severity.MAJOR_ALARM, Severity.MAJOR_ALARM, STATUS.ERROR),
            (Severity.MAJOR_ALARM, Severity.MINOR_ALARM, STATUS.ERROR),
            (Severity.MAJOR_ALARM, Severity.INVALID_ALARM, STATUS.ERROR),
            (Severity.MINOR_ALARM, Severity.MINOR_ALARM, STATUS.WARNING),
            (Severity.MINOR_ALARM, Severity.INVALID_ALARM, STATUS.WARNING),
            (Severity.INVALID_ALARM, Severity.INVALID_ALARM, STATUS.UNKNOWN),
        ]
    )
    def test_GIVEN_different_severity_levels_WHEN_adding_problems_THEN_server_status_reflects_highest_severity(
        self, problem_severity_1, problem_severity_2, expected
    ):
        problem_description_1 = "problem_description_1"
        problem_description_2 = "problem_description_2"
        source = Mock()
        problem_1 = ProblemInfo(problem_description_1, source, problem_severity_1)
        problem_2 = ProblemInfo(problem_description_2, source, problem_severity_2)

        self.status_manager.update_active_problems(problem_1)
        self.status_manager.update_active_problems(problem_2)
        actual = self.status_manager.status

        self.assertEqual(expected, actual)

    def test_GIVEN_initial_state_WHEN_error_log_THEN_list_is_blank(self):
        expected = []

        actual = self.status_manager._error_log

        self.assertEqual(expected, actual)

    def test_WHEN_error_messages_added_THEN_messages_contained_in_log_list(self):
        message_1 = "error_log_message"
        message_2 = "error_log_message_2"
        expected = [message_1, message_2]
        self.status_manager.update_error_log(message_1)
        self.status_manager.update_error_log(message_2)

        actual = self.status_manager._error_log

        self.assertEqual(expected, actual)

    def test_GIVEN_error_log_not_empty_WHEN_status_cleared_THEN_error_log_is_emptied(self):
        message_1 = "error_log_message"
        message_2 = "error_log_message_2"
        expected = []
        self.status_manager.update_error_log(message_1)
        self.status_manager.update_error_log(message_2)

        self.status_manager.clear_all()
        actual = self.status_manager._error_log

        self.assertEqual(expected, actual)
