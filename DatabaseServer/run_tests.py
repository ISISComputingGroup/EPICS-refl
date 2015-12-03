# Add root path for access to server_commons
import os
import sys
os.environ["MYDIRBLOCK"] = os.path.abspath('..')
sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))
# Standard imports
import unittest
import xmlrunner
import argparse

from test_modules.sqlite_wrapper_tests import TestSqliteWrapperSequence
from test_modules.mysql_wrapper_tests import TestMySQLWrapperSequence
from test_modules.options_holder_tests import TestOptionsHolderSequence
from test_modules.database_server_test_mysql import TestDatabaseServer

DEFAULT_DIRECTORY = os.path.join('..','..','..','..','test-reports')

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    sqlite_suite = unittest.TestLoader().loadTestsFromTestCase(TestSqliteWrapperSequence)
    mysql_suite = unittest.TestLoader().loadTestsFromTestCase(TestMySQLWrapperSequence)
    options_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestOptionsHolderSequence)
    database_server_suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabaseServer)

    print "\n\n------ BEGINNING UNIT TESTS ------"
    xmlrunner.XMLTestRunner(output=xml_dir).run(sqlite_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(mysql_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(options_holder_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(database_server_suite)
    print "------ UNIT TESTS COMPLETE ------\n\n"
