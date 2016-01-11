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

from BlockServer.site_specific.default.test_modules.block_rules_tests import TestBlockRulesSequence

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

    # Site specific tests
    block_rules_suite = unittest.TestLoader().loadTestsFromTestCase(TestBlockRulesSequence)

    print "\n\n------ BEGINNING BLOCKSERVER UNIT TESTS ------"

    xmlrunner.XMLTestRunner(output=xml_dir).run(configuration_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_xml_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_json_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(active_config_holder_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(container_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_holder_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(inactive_config_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(file_watcher_event_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(schema_checker_event_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(synoptic_manager_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(ioc_control_suite)

    # Site specific tests
    xmlrunner.XMLTestRunner(output=xml_dir).run(block_rules_suite)

    print "------ BLOCKSERVER UNIT TESTS COMPLETE ------\n\n"
