import threading
import time
import unittest
from Queue import Queue, Empty

from concurrent.futures import wait
from mock import Mock, patch

from hamcrest import *

import server_common
from server_common.channel_access import ChannelAccess, NUMBER_OF_CAPUT_THREADS


thread_ids = Queue()
thread_calls = Queue()

def set_pv_value(name, value, wait=False, timeout=0):
    """ Mock method with set pv value signature, must take some time to work"""
    thread_calls.put((name, value, wait, timeout))
    thread_ids.put(threading.currentThread().ident)
    time.sleep(0.5)

def empty_queue(queue):
    contents = []
    try:
        while True:
            contents.append(queue.get(block=False))
    except Empty:
        pass
    return contents


class TestChannelAccess(unittest.TestCase):
    # throughout this class I would like to have patch the static method set_pv_value but it doesn't work because it is
    # static is a thread

    def setUp(self):
        empty_queue(thread_ids)
        empty_queue(thread_calls)
        ChannelAccess.wait_for_tasks()


    def test_WHEN_ca_put_and_not_wait_THEN_get_pv_value_is_called(self):
        expected_val = 10

        future = ChannelAccess.caput("block", expected_val, False, set_pv_value=set_pv_value)

        wait([future])
        time.sleep(3)  # wait for all items to finish
        assert_that(len(empty_queue(thread_calls)), is_(1), "call is called once")


    def test_WHEN_multiple_ca_puts_and_not_wait_THEN_thread_count_is_limited(self):
        initial_thread_count = threading.active_count()

        the_future = []
        for thread_val in range(2 * NUMBER_OF_CAPUT_THREADS):
            the_future.append(ChannelAccess.caput("Non_existant_block", thread_val, False, set_pv_value=set_pv_value))

        current_count = threading.active_count()

        newly_created_threads = current_count - initial_thread_count
        assert_that(newly_created_threads, is_(greater_than(NUMBER_OF_CAPUT_THREADS / 2)),
                    "Number of threads running (thread count: initial {} current {})".format(initial_thread_count,
                                                                                             current_count))

        assert_that(newly_created_threads, is_(less_than_or_equal_to(NUMBER_OF_CAPUT_THREADS)),
                    "Number of threads running (thread count: initial {} current {})".format(initial_thread_count,
                                                                                             current_count))

        wait(the_future)
        time.sleep(3)  # wait for all items to finish
        assert_that(len(empty_queue(thread_calls)), is_(2 * NUMBER_OF_CAPUT_THREADS))

    def test_WHEN_multiple_ca_puts_THEN_a_limited_number_of_threads_are_used(self):
        # This is so the same ca context and channels are used

        the_future = []
        for thread_val in range(2 * NUMBER_OF_CAPUT_THREADS):
            the_future.append(ChannelAccess.caput("Non_existent_block", thread_val, False, set_pv_value=set_pv_value))

        wait(the_future)
        time.sleep(3)  # wait for all items to finish

        ids=set(empty_queue(thread_ids))

        assert_that(ids, has_length(NUMBER_OF_CAPUT_THREADS),
                    "Number of ids should be the same as number of threads so that multiple tasks use the same thread")
