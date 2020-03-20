import threading
import time
import unittest

from concurrent.futures import wait
from mock import Mock, patch

from hamcrest import *

import server_common
from server_common.channel_access import ChannelAccess, NUMBER_OF_CAPUT_THREADS


def set_pv_value(name, value, wait=False, timeout=0):
    """ Mock method with set pv value signature, must take some time to work"""
    time.sleep(1)


class TestChannelAccess(unittest.TestCase):

    @patch("server_common.channel_access.CaChannelWrapper.set_pv_value")
    def test_WHEN_ca_put_and_not_wait_THEN_get_pv_value_is_called(self, mock_set_pv_value):
        expected_val = 10

        future = ChannelAccess.caput("block", expected_val, False)

        wait([future])
        mock_set_pv_value.assert_called_once_with("block", expected_val, False)

    @patch("server_common.channel_access.CaChannelWrapper.set_pv_value", side_effect=set_pv_value)
    def test_WHEN_multiple_ca_puts_and_not_wait_THEN_thread_count_is_limited(self, mock_set_pv_value):
        initial_thread_count = threading.active_count()

        the_future = []
        for thread_val in range(2 * NUMBER_OF_CAPUT_THREADS):
            the_future.append(ChannelAccess.caput("Non_existant_block", thread_val, False))

        current_count = threading.active_count()

        newly_created_threads = current_count - initial_thread_count
        assert_that(newly_created_threads, is_(greater_than(NUMBER_OF_CAPUT_THREADS / 2)),
                    "Number of threads running (thread count: initial {} current {})".format(initial_thread_count,
                                                                                             current_count))

        assert_that(newly_created_threads, is_(less_than_or_equal_to(NUMBER_OF_CAPUT_THREADS)),
                    "Number of threads running (thread count: initial {} current {})".format(initial_thread_count,
                                                                                             current_count))

        wait(the_future)
        assert_that(mock_set_pv_value.call_count, is_(2 * NUMBER_OF_CAPUT_THREADS))
