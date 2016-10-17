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

import os
import string

from lxml import etree

from BlockServer.core.constants import SCHEMA_FOR, FILENAME_COMPONENTS
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


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
    """ The ConfigurationSchemaChecker class

    Contains utilities to check configurations against xml schema.
    """
    @staticmethod
    def check_xml_data_matches_schema(schema_filepath, xml_data):
        """ This method takes xml data and checks it against a given schema.

        A ConfigurationInvalidUnderSchema error is raised if the file is incorrect.

        Args:
            schema_filepath (string): The location of the schema file
            synoptic_xml_data (string): The XML for the screens
        """
        folder, file_name = string.rsplit(schema_filepath, os.sep, 1)
        xmlparser = ConfigurationSchemaChecker._import_schema(folder, file_name)

        try:
            etree.fromstring(xml_data, xmlparser)
        except etree.XMLSyntaxError as err:
            raise ConfigurationInvalidUnderSchema(str(err.message))

    @staticmethod
    def check_xml_matches_schema(schema_filepath, screen_xml_data, object_type):
        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(schema_filepath, screen_xml_data)
        except ConfigurationInvalidUnderSchema as err:
            raise ConfigurationInvalidUnderSchema(
                "{object_type} incorrectly formatted: {err}".format(object_type=object_type, err=str(err.value)))

    @staticmethod
    def _check_file_against_schema(xml_file, schema_folder, schema_file):
        """ This method takes an xml file and checks it against a given schema.

        Args:
            xml_file (string): The XML file to check
            schema_folder (string): The location of the schema files
            schema_file (string): The schema file to use

        Raises:
            etree.XMLSyntaxError : Raised if the file is incorrect
        """
        xmlparser = ConfigurationSchemaChecker._import_schema(schema_folder, schema_file)

        # Import the xml file
        with open(xml_file, 'r') as f:
            xml = f.read()

        etree.fromstring(xml, xmlparser)

    @staticmethod
    def _import_schema(schema_folder, schema_file):
        # Import the schema file (must move to path for includes)
        cur = os.getcwd()
        os.chdir(schema_folder)
        with open(schema_file, 'r') as f:
            schema_raw = etree.XML(f.read())

        conf_schema = etree.XMLSchema(schema_raw)
        xmlparser = etree.XMLParser(schema=conf_schema)
        os.chdir(cur)

        return xmlparser
