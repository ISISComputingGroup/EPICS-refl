import os
import unittest


def load_tests(loader, standard_tests, pattern):
    """
    This function is needed by the load_tests protocol described at
    https://docs.python.org/3/library/unittest.html#load-tests-protocol

    The tests in this module are only added under Python 3.
    """
    standard_tests.addTests(loader.discover(os.path.dirname(__file__), pattern=pattern))
    return standard_tests
