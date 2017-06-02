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

from lxml import etree
import argparse
import os

def validate(schema_file, xml_file):
    print "\nTrying to valid %s using %s" % (schema_file, xml_file)
    try:
        # Import the schema file (must move to path for includes)
        cur = os.getcwd()
        os.chdir(self._schema_folder)
        with open(schema_file, 'r') as f:
            schema_raw = etree.XML(f.read())
        schema = etree.XMLSchema(schema_raw)
        xmlparser = etree.XMLParser(schema=schema)
        os.chdir(cur)
        # Import the xml file
        with open(xml_file, 'r') as f:
            str = f.read()
        etree.fromstring(str, xmlparser)
        print "Successfully validated"
    except Exception as err:
        print "Failed to validate"
        print err

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config_folder')
    parser.add_argument('schema_folder')
    args = parser.parse_args()
    
    conf_path = os.path.abspath(args.config_folder)
    schema_path = os.path.abspath(args.schema_folder)
    
    print "Configuration folder: %s" % conf_path
    print "Schema folder: %s" % schema_path
    
    validate("%s\\blocks.xsd" % schema_path, "%s\\blocks.xml" % conf_path)
    validate("%s\\groups.xsd" % schema_path, "%s\\groups.xml" % conf_path)
    validate("%s\\components.xsd" % schema_path, "%s\\components.xml" % conf_path)
    validate("%s\\iocs.xsd" % schema_path, "%s\\iocs.xml" % conf_path)
