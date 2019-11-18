# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2018 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Run all inst server tests
"""

# Standard imports
import os
import sys
import unittest

import six
import xmlrunner
import argparse
from coverage import Coverage
try:
    from contextlib import contextmanager, nullcontext
except ImportError:
    from contextlib2 import contextmanager, nullcontext

DEFAULT_DIRECTORY = os.path.join('..', '..', '..', 'test-reports')


@contextmanager
def coverage_analysis():
    cov = Coverage()
    cov.start()
    try:
        yield
    finally:
        cov.stop()
        cov.report()
        print("------  SAVING COVERAGE REPORTS ------ ")
        cov.xml_report(outfile=os.path.join(".", 'cobertura.xml'))


if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    test_suite = unittest.TestLoader().discover(os.path.dirname(__file__), pattern="test_*")

    ret_vals = None

    # Python 2 coverage analysis does not understand the Py3 code in some modules, and crashes out.
    with nullcontext() if six.PY2 else coverage_analysis():
        print("\n\n------ BEGINNING INST SERVERS UNIT TESTS ------")
        ret_vals = xmlrunner.XMLTestRunner(output=xml_dir, verbosity=2).run(test_suite)
        print("------ INST SERVERS UNIT TESTS COMPLETE ------\n\n")

    # Return failure exit code if a test errored or failed
    sys.exit(bool(ret_vals.errors or ret_vals.failures))
