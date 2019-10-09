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

from collections import OrderedDict
from server_common.utilities import print_and_log, parse_xml_removing_namespace
import os
from ioc_options import IocOptions

TAG_NAME = 'name'
TAG_VALUE = 'value'
TAG_IOC_CONFIG = 'ioc_config'
CONFIG_PART = 'config_part'
TAG_PATTERN = 'pattern'
TAG_DESCRIPTION = 'description'
TAG_DEFAULT = 'defaultValue'
TAG_HAS_DEFAULT = 'hasDefault'


def create_xpath_search(group, individual):
    return "./{}/{}/{}".format(CONFIG_PART, group, individual)


MACROS = create_xpath_search('macros', 'macro')
PVS = create_xpath_search('pvs', 'pv')
PVSETS = create_xpath_search('pvsets', 'pvset')


class OptionsLoader(object):
    @staticmethod
    def get_options(path):
        """Loads the IOC options from file and converts them into IocOptions objects

        Args:
            path (string): The path to the xml file to be loaded

        Returns:
            OrderedDict : A dict of IOCs and their associated options
        """
        iocs = OrderedDict()
        if os.path.isfile(path):
            root = parse_xml_removing_namespace(path)
            OptionsLoader._options_from_xml(root, iocs)
        else:
            print_and_log("Cannot find config path: " + str(path), "MINOR")
        return iocs

    @staticmethod
    def _options_from_xml(root_xml, iocs):
        """Populates the supplied list of iocs based on an XML tree within a config.xml file"""
        for ioc in root_xml.findall("./" + TAG_IOC_CONFIG):
            name = ioc.attrib[TAG_NAME]
            if name is not None and name != "":
                iocs[name.upper()] = IocOptions(name.upper())
                # Get any macros
                for macro in ioc.findall(MACROS):
                    iocs[name.upper()].macros[macro.attrib[TAG_NAME]] = {TAG_DESCRIPTION: macro.attrib[TAG_DESCRIPTION],
                                                                         TAG_PATTERN: macro.attrib.get(TAG_PATTERN),
                                                                         TAG_DEFAULT: macro.attrib.get(TAG_DEFAULT),
                                                                         TAG_HAS_DEFAULT: macro.attrib.get(TAG_HAS_DEFAULT)}

                # Get any pvsets
                for pvset in ioc.findall(PVSETS):
                    iocs[name.upper()].pvsets[pvset.attrib[TAG_NAME]] = {TAG_DESCRIPTION: pvset.attrib[TAG_DESCRIPTION]}

                # Get any pvs
                for pv in ioc.findall(PVS):
                    iocs[name.upper()].pvs[pv.attrib[TAG_NAME]] = {TAG_DESCRIPTION: pv.attrib[TAG_DESCRIPTION]}
