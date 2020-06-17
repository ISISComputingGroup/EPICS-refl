from __future__ import unicode_literals, absolute_import, print_function, division

import re
import unittest
import os
from datetime import datetime

from hamcrest import *
from mock import Mock, patch

from server_common.loggers.isis_logger import IsisLogger, IsisPutLog

TEMP_FOLDER = os.path.join("C:\\", "instrument", "var", "tmp", "autosave_tests")


class TestISISLog(unittest.TestCase):

    def setUp(self):
        IsisLogger.executor = None
        IsisLogger.start_thread_pool()

    @patch('socket.socket')
    def test_GIVEN_logger_WHEN_message_sent_THEN_message_contents_is_correct(self, socket_mock):
        message = "my message"

        logger = IsisLogger()
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_to_log(message)
        logger.stop_thread_pool()

        sent_xml = mock_socket.sendall.call_args[0][0]
        assert_that(str(sent_xml), contains_string(message))

    @patch('socket.socket')
    def test_GIVEN_logger_WHEN_message_sent_THEN_connection_on_logger_port_is_opened_and_close(self, socket_mock):
        logger = IsisLogger()
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_to_log("hi")
        logger.stop_thread_pool()

        mock_socket.connect.assert_called_once_with(("127.0.0.1", 7004))
        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_GIVEN_logger_WHEN_message_sent_THEN_message_contains_ioc_name(self, socket_mock):
        expected_ioc_name = "my_ioc_name"

        logger = IsisLogger()
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_to_log("message", src=expected_ioc_name)
        IsisLogger.executor.shutdown(wait=True)

        sent_xml = mock_socket.sendall.call_args[0][0]
        assert_that(str(sent_xml), contains_string(expected_ioc_name))

    @patch('socket.socket')
    def test_GIVEN_logger_with_ioc_name_WHEN_message_sent_THEN_message_contains_ioc_name(self, socket_mock):
        expected_ioc_name = "my_ioc_name"

        logger = IsisLogger(ioc_name=expected_ioc_name)
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_to_log("message")
        IsisLogger.executor.shutdown(wait=True)

        sent_xml = mock_socket.sendall.call_args[0][0]
        assert_that(str(sent_xml), contains_string(expected_ioc_name))

    @patch('socket.socket')
    def test_GIVEN_logger_with_ioc_name_WHEN_message_sent_with_ioc_name_THEN_message_contains_sent_ioc_name(
            self, socket_mock):
        expected_ioc_name = "my_ioc_name"

        logger = IsisLogger("different_ioc_name")
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_to_log("message", src=expected_ioc_name)
        IsisLogger.executor.shutdown(wait=True)

        sent_xml = mock_socket.sendall.call_args[0][0]
        assert_that(str(sent_xml), contains_string(expected_ioc_name))

    @patch('socket.socket')
    @patch('datetime.datetime')
    def test_GIVEN_isis_put_log_WHEN_pv_set_THEN_message_is_correct(self, datetime_mock, socket_mock):
        expected_ioc_name = "my_ioc_name"
        expected_date = "10-Jan-19 12:34:56"
        datetime_mock.now.return_value = datetime(2019, 1, 10, 12, 34, 56)
        pv_name = "pv:name"
        new_value = 19
        old_value = 10.23
        expected_message = "{} 127.0.0.1 {} {} {} {}".format(
            expected_date, expected_ioc_name, pv_name, new_value, old_value)

        logger = IsisPutLog(expected_ioc_name)
        mock_socket = Mock()
        socket_mock.return_value = mock_socket

        logger.write_pv_put(pv_name, new_value, old_value)
        IsisLogger.executor.shutdown(wait=True)

        sent_xml = mock_socket.sendall.call_args[0][0]
        match = re.search("<!\[CDATA\[(.*)\]\]>", str(sent_xml))
        assert_that(match.group(1), is_(expected_message))
