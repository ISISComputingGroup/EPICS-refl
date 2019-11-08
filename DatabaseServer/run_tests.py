from __future__ import print_function, absolute_import, division, unicode_literals
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
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

# Add root path for access to server_commons
import os
import sys

os.environ["MYDIRBLOCK"] = os.path.abspath('..')
sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))
# Standard imports
import unittest
import xmlrunner
import argparse


DEFAULT_DIRECTORY = os.path.join('..', '..', '..', '..', 'test-reports')

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_modules"))
    test_suite = unittest.TestLoader().discover(test_dir, pattern="test_*.py")

    print("\n\n------ BEGINNING DATABASE SERVER UNIT TESTS ------")
    ret_vals = xmlrunner.XMLTestRunner(output=xml_dir).run(test_suite)
    print("------ DATABASE SERVER UNIT TESTS COMPLETE ------\n\n")

    # Return failure exit code if a test failed
    sys.exit(bool(ret_vals.errors or ret_vals.failures))
