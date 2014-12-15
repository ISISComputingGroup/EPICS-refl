import unittest
import xmlrunner
import argparse

from test_modules.config_server_tests import TestConfigServerSequence
from test_modules.configuration_tests import TestConfigurationSequence
from test_modules.configuration_xml_tests import TestConfigurationXmlConverterSequence
from test_modules.configuration_json_tests import TestConfigurationJsonConverterSequence
from test_modules.container_tests import TestContainersSequence
from test_modules.config_holder_tests import TestConfigHolderSequence

DEFAULT_DIRECTORY = '..\\..\\..\\test-reports'

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
    config_server_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigServerSequence)
    container_suite = unittest.TestLoader().loadTestsFromTestCase(TestContainersSequence)
    config_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigHolderSequence)
    options_holder_suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigHolderSequence)

    print "\n\n------ BEGINNING BLOCKSERVER UNIT TESTS ------"
    xmlrunner.XMLTestRunner(output=xml_dir).run(configuration_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_xml_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_json_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_server_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(container_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(config_holder_suite)
    xmlrunner.XMLTestRunner(output=xml_dir).run(options_holder_suite)
    print "------ BLOCKSERVER UNIT TESTS COMPLETE ------\n\n"
