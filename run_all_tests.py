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

# Standard imports
import os
import sys
import glob
import unittest
import xmlrunner
import argparse

DEFAULT_DIRECTORY = os.path.join('..', '..', '..', 'test-reports')

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]
    ret_vals = list()

    for folder in glob.glob(os.path.join(os.path.dirname(__file__), "*", "test_modules")):
        # Load tests from test suites
        test_dir = os.path.abspath(folder)

        test_suite = unittest.TestLoader().discover(test_dir, pattern="test_*.py")
        print ("\n\n------ BEGINNING {} UNIT TESTS ------".format(folder.split(os.sep)[-2]))
        ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(test_suite))
        print ("------ UNIT TESTS COMPLETE ------\n\n")

        # Return failure exit code if a test failed
    sys.exit(False in ret_vals)
