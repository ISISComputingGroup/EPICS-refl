import unittest

from mock import Mock

from ReflectometryServer.server_status_manager import _ServerStatusManager, STATUS, PROBLEM


class TestStatusManager(unittest.TestCase):
    def setUp(self):
        self.status_manager = _ServerStatusManager()

    def test_WHEN_status_and_message_set_THEN_status_manager_holds_correct_values(self):
        expected_status = STATUS.GENERAL_ERROR
        expected_message = "error_message"

        self.status_manager.update_status(expected_status, expected_message)
        actual_status = self.status_manager.status
        actual_message = self.status_manager.message

        self.assertEqual(expected_status, actual_status)
        self.assertEqual(expected_message, actual_message)

    def test_GIVEN_initial_state_WHEN_reading_server_problems_THEN_list_is_blank(self):
        expected = {}

        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_new_source_WHEN_new_problem_occurs_THEN_new_problem_added_as_key_with_source_as_value(self):
        problem = PROBLEM.PLACEHOLDER
        source = Mock()
        expected = {problem: {source}}

        self.status_manager.update_active_problems(problem, source)
        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_new_source_WHEN_known_problem_occurs_THEN_problem_entry_modified_by_adding_another_source(self):
        problem = PROBLEM.PLACEHOLDER
        source_1 = Mock()
        source_2 = Mock()
        expected = {problem: {source_1, source_2}}

        self.status_manager.update_active_problems(problem, source_1)
        self.status_manager.update_active_problems(problem, source_2)
        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_known_source_WHEN_new_problem_occurs_THEN_new_problem_added_as_key_with_source_as_value(self):
        problem_1 = PROBLEM.PLACEHOLDER
        problem_2 = PROBLEM.PLACEHOLDER2
        source = Mock()
        expected = {problem_1: {source}, problem_2: {source}}

        self.status_manager.update_active_problems(problem_1, source)
        self.status_manager.update_active_problems(problem_2, source)
        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_known_source_WHEN_known_problem_occurs_THEN_problem_not_added_again(self):
        problem = PROBLEM.PLACEHOLDER
        source = Mock()
        expected = {problem: {source}}

        self.status_manager.update_active_problems(problem, source)
        self.status_manager.update_active_problems(problem, source)
        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_non_empty_list_of_problems_WHEN_server_status_cleared_THEN_all_problems_are_cleared(self):
        problem_1 = PROBLEM.PLACEHOLDER
        problem_2 = PROBLEM.PLACEHOLDER2
        source = Mock()
        expected = {}
        self.status_manager.update_active_problems(problem_1, source)
        self.status_manager.update_active_problems(problem_2, source)

        self.status_manager.clear_all()
        actual = self.status_manager.active_problems

        self.assertEqual(expected, actual)

    def test_GIVEN_initial_state_WHEN_error_log_THEN_list_is_blank(self):
        expected = []

        actual = self.status_manager.error_log

        self.assertEqual(expected, actual)

    def test_WHEN_error_messages_added_THEN_messages_contained_in_log_list(self):
        message_1 = "error_log_message"
        message_2 = "error_log_message_2"
        expected = [message_1, message_2]
        self.status_manager.update_log(message_1)
        self.status_manager.update_log(message_2)

        actual = self.status_manager.error_log

        self.assertEqual(expected, actual)

    def test_GIVEN_error_log_not_empty_WHEN_status_cleared_THEN_error_log_is_emptied(self):
        message_1 = "error_log_message"
        message_2 = "error_log_message_2"
        expected = []
        self.status_manager.update_log(message_1)
        self.status_manager.update_log(message_2)

        self.status_manager.clear_all()
        actual = self.status_manager.error_log

        self.assertEqual(expected, actual)