from collections import OrderedDict
from server_common.utilities import print_and_log, parse_xml_removing_namespace
import os
from ioc_options import IocOptions

TAG_NAME = 'name'
TAG_VALUE = 'value'
TAG_MACRO = 'macro'
TAG_PV = 'pv'
TAG_PVSET = 'pvset'
TAG_IOC_CONFIG = 'ioc_config'
CONFIG_PART = 'config_part'
TAG_PATTERN = 'pattern'
TAG_DESCRIPTION = 'description'
TAG_MACROS = 'macros'
TAG_PVS = 'pvs'
TAG_PVSETS = 'pvsets'


class OptionsLoader(object):
    @staticmethod
    def get_options(path):
        """Loads the IOC options from file and converts them into IocOptions objects

        Args:
            path (string) : The path to the xml file to be loaded

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
        iocs_xml = root_xml.findall("./" + TAG_IOC_CONFIG)
        for i in iocs_xml:
            n = i.attrib[TAG_NAME]
            if n is not None and n != "":
                iocs[n.upper()] = IocOptions(n.upper())

                # Get any macros
                macros_xml = i.findall("./" + CONFIG_PART + "/" + TAG_MACROS + "/" + TAG_MACRO)
                for m in macros_xml:
                    iocs[n.upper()].macros[m.attrib[TAG_NAME]] = {TAG_DESCRIPTION: m.attrib[TAG_DESCRIPTION],
                                                                  TAG_PATTERN: m.attrib.get(TAG_PATTERN)}

                # Get any pvsets
                pvsets_xml = i.findall("./" + CONFIG_PART + "/" + TAG_PVSETS + "/" + TAG_PVSET)
                for p in pvsets_xml:
                    iocs[n.upper()].pvsets[p.attrib[TAG_NAME]] = {TAG_DESCRIPTION: p.attrib[TAG_DESCRIPTION]}

                # Get any pvs
                pvs_xml = i.findall("./" + CONFIG_PART + "/" + TAG_PVS + "/" + TAG_PV)
                for p in pvs_xml:
                    iocs[n.upper()].pvs[p.attrib[TAG_NAME]] = {TAG_DESCRIPTION: p.attrib[TAG_DESCRIPTION]}