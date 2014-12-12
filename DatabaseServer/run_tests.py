import unittest
import xmlrunner
import argparse

from test_modules.sqlite_wrapper_tests import TestSqliteWrapperSequence
from test_modules.options_holder_tests import TestOptionsHolderSequence


DEFAULT_DIRECTORY = '..\\..\\test-reports'

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    sqlite_suite = unittest.TestLoader().loadTestsFromTestCase(TestSqliteWrapperSequence)
    options_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestOptionsHolderSequence)

    print "\n\n------ BEGINNING UNIT TESTS ------"
    xmlrunner.XMLTestRunner(output=xml_dir).run(sqlite_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(options_holder_suite)
    print "------ UNIT TESTS COMPLETE ------\n\n"
