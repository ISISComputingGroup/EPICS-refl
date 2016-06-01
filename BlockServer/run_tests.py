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
# Set MYDIRBLOCK so that example_base can be found
os.environ["MYDIRBLOCK"] = ".."
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath(os.path.join("..","..","..","ConfigVersionControl","master")))
# Standard imports
import unittest
import xmlrunner
import argparse

from BlockServer.test_modules.active_config_holder_tests import TestActiveConfigHolderSequence
from BlockServer.test_modules.configuration_tests import TestConfigurationSequence
from BlockServer.test_modules.configuration_xml_tests import TestConfigurationXmlConverterSequence
from BlockServer.test_modules.configuration_json_tests import TestConfigurationJsonConverterSequence
from BlockServer.test_modules.container_tests import TestContainersSequence
from BlockServer.test_modules.config_holder_tests import TestConfigHolderSequence
from BlockServer.test_modules.config_list_manager_tests import TestInactiveConfigsSequence
from BlockServer.test_modules.file_event_handler_tests import TestFileEventHandler
from BlockServer.test_modules.schema_checker_tests import TestSchemaChecker
from BlockServer.test_modules.synoptic_manager_tests import TestSynopticManagerSequence
from BlockServer.test_modules.ioc_control_tests import TestIocControlSequence
from BlockServer.test_modules.file_path_manager_tests import TestFilePathManagerSequence
from BlockServer.site_specific.default.test_modules.block_rules_tests import TestBlockRulesSequence
from BlockServer.test_modules.runcontrol_manager_tests import TestRunControlSequence
from BlockServer.site_specific.default.test_modules.group_rules_tests import TestGroupRulesSequence

DEFAULT_DIRECTORY = os.path.join('..','..','..','..','test-reports')

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    configuration_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigurationSequence)
    config_xml_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigurationXmlConverterSequence)
    config_json_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigurationJsonConverterSequence)
    active_config_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestActiveConfigHolderSequence)
    container_suite = unittest.TestLoader().loadTestsFromTestCase(TestContainersSequence)
    config_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigHolderSequence)
    inactive_config_suite = unittest.TestLoader().loadTestsFromTestCase(TestInactiveConfigsSequence)
    file_watcher_event_suite = unittest.TestLoader().loadTestsFromTestCase(TestFileEventHandler)
    schema_checker_event_suite = unittest.TestLoader().loadTestsFromTestCase(TestSchemaChecker)
    synoptic_manager_suite = unittest.TestLoader().loadTestsFromTestCase(TestSynopticManagerSequence)
    ioc_control_suite = unittest.TestLoader().loadTestsFromTestCase(TestIocControlSequence)
    file_path_manager_suite = unittest.TestLoader().loadTestsFromTestCase(TestFilePathManagerSequence)

    # Site specific tests
    block_rules_suite = unittest.TestLoader().loadTestsFromTestCase(TestBlockRulesSequence)
    runcontrol_suite = unittest.TestLoader().loadTestsFromTestCase(TestRunControlSequence)
    group_rules_suite = unittest.TestLoader().loadTestsFromTestCase(TestGroupRulesSequence)

    print "\n\n------ BEGINNING BLOCKSERVER UNIT TESTS ------"

    ret_vals = list()
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(configuration_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(config_xml_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(config_json_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(active_config_holder_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(container_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(config_holder_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(inactive_config_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(file_watcher_event_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(schema_checker_event_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(synoptic_manager_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(ioc_control_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(file_path_manager_suite).wasSuccessful())

    # Site specific tests
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(block_rules_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(runcontrol_suite).wasSuccessful())
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(group_rules_suite).wasSuccessful())

    print "------ BLOCKSERVER UNIT TESTS COMPLETE ------\n\n"
    # Return failure exit code if a test failed
    sys.exit(False in ret_vals)
