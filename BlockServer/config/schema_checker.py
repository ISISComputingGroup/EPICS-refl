import os
import string
from lxml import etree
from constants import SCHEMA_FOR, COMPONENT_DIRECTORY, CONFIG_DIRECTORY, FILENAME_SUBCONFIGS


class NotConfigFileException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ConfigurationIncompleteException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ConfigurationInvalidUnderSchema(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ConfigurationSchemaChecker(object):
    @staticmethod
    def check_all_config_files_correct(schema_folder, root_path):
        valid = True

        for root, dirs, files in os.walk(root_path + CONFIG_DIRECTORY):
            for f in files:
                full_path = os.path.join(root, f)
                valid &= ConfigurationSchemaChecker.check_matches_schema(schema_folder, full_path)

        for root, dirs, files in os.walk(root_path + COMPONENT_DIRECTORY):
            for f in files:
                full_path = os.path.join(root, f)
                valid &= ConfigurationSchemaChecker.check_matches_schema(schema_folder, full_path, True)

        return valid

    @staticmethod
    def check_matches_schema(schema_folder, config_xml_path, is_subconfig=False):
        folder, file_name = string.rsplit(config_xml_path, '\\', 1)
        if file_name in SCHEMA_FOR:
            schema_name = string.split(file_name, '.')[0] + '.xsd'
            try:
                ConfigurationSchemaChecker._check_against_schema(config_xml_path, schema_folder, schema_name)
            except etree.XMLSyntaxError as err:
                raise ConfigurationInvalidUnderSchema(config_xml_path + " incorrectly formatted: " + str(err.message))
        else:
            if file_name != "":
                raise NotConfigFileException("File in " + config_xml_path + " not known config xml (%s)" % file_name)

        missing_files = set(SCHEMA_FOR).difference(set(os.listdir(folder)))
        if len(missing_files) != 0:
            if not (is_subconfig and missing_files == [FILENAME_SUBCONFIGS]):
                raise ConfigurationIncompleteException("Files missing in " + config_xml_path +
                                                       " (%s)" % ','.join(list(missing_files)))

        return True

    @staticmethod
    def _check_against_schema(xml_file, schema_folder, schema_file):
        """ This method takes an xml file and checks it against a given schema.
        A ConfigurationInvalidUnderSchema error is raised if the file is incorrect """

        # Import the schema file (must move to path for includes)
        cur = os.getcwd()
        os.chdir(schema_folder)
        with open(schema_file, 'r') as f:
            schema_raw = etree.XML(f.read())

        schema = etree.XMLSchema(schema_raw)
        xmlparser = etree.XMLParser(schema=schema)
        os.chdir(cur)

        # Import the xml file
        with open(xml_file, 'r') as f:
            xml = f.read()

        etree.fromstring(xml, xmlparser)
