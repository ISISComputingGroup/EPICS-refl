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
sys.path.insert(0, os.path.abspath(".."))

# Standard imports
import unittest
import xmlrunner
import argparse

from BlockServerToKafka.test_modules.test_block_server_monitor import TestBlockServerMonitor
from BlockServerToKafka.test_modules.test_forwarder_config import TestForwarderConfig

DEFAULT_DIRECTORY = os.path.join('..', '..', '..', '..', 'test-reports')

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    block_server_monitor_suite = unittest.TestLoader().loadTestsFromTestCase(TestBlockServerMonitor)
    forwarder_config_suite = unittest.TestLoader().loadTestsFromTestCase(TestForwarderConfig)

    print("\n\n------ BEGINNING BLOCK_SERVER_TO_KAFKA UNIT TESTS ------")
    ret_vals = []
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(block_server_monitor_suite))
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(forwarder_config_suite))
    print("------ BLOCK_SERVER_TO_KAFKA UNIT TESTS COMPLETE ------\n\n")

    # Return failure exit code if a test failed
    sys.exit(False in ret_vals)
