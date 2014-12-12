from collections import OrderedDict

from config.constants import GRP_NONE
from config.xml_converter import ConfigurationXmlConverter


class MockConfiguration(object):
    def __init__(self):
        # variables set when the class under test calls mock functions to be read by the testing code
        self.add_block_called = False
        self.remove_block_called = False
        self.edit_block_called = False
        self.add_block_parameters = []
        self.remove_block_parameters = []
        self.edit_block_parameters = []
        # variables set by the testing code to be fed to the class under test when it calls mock functions
        self.block_names = []
        self.blocks = OrderedDict()

    def add_block(self, name, read_pv, group=GRP_NONE, local=True, visible=True):
        self.add_block_called = True
        self.add_block_parameters = [name, read_pv, group, local, visible]

    def remove_block(self, name):
        self.remove_block_called = True
        self.remove_block_parameters = [name]

    def edit_block(self, name, read_pv, group, local, new_name=None):
        self.edit_block_called = True
        self.edit_block_parameters = [name, read_pv, group, local, new_name]

    def get_block_names(self):
        return self.block_names


class MockConfigurationFileManager(object):
    def __init__(self):
        self.blocks_xml = ""
        self.groups_xml = ""
        self.iocs_xml = ""
        self.subconfigs_xml = ""

    @staticmethod
    def load_config(configuration, root_path, config_name):
        pass

    def save_config(self, configuration, root_path, config_name):
        self.blocks_xml = ConfigurationXmlConverter.blocks_to_xml(configuration.blocks, configuration.macros)
        self.groups_xml = ConfigurationXmlConverter.groups_to_xml(configuration.groups)
        self.iocs_xml = ConfigurationXmlConverter.iocs_to_xml(configuration.iocs)
        self.subconfigs_xml = ConfigurationXmlConverter.subconfigs_to_xml(configuration.subconfigs)


class MockConfigurationXmlConverter(object):
    def __init__(self):
        self.blocks_xml = ""
        self.groups_xml = ""
        self.iocs_xml = ""
        self.subconfigs_xml = ""

    def blocks_to_xml(self, blocks, macros):
        return self.blocks_xml

    def groups_to_xml(self, groups, include_none=False):
        return self.groups_xml

    def iocs_to_xml(self, iocs):
        return self.iocs_xml

    def subconfigs_to_xml(self, subconfigs):
        return self.subconfigs_xml

    @staticmethod
    def groups_from_xml(xml, groups, blocks):
        pass

    @staticmethod
    def groups_from_xml_string(root_xml, groups, blocks):
        pass


class MockConfigurationJsonConverter(object):
    def __init__(self):
        self.blocks_json = ""

    def blocks_to_json(self, blocks, pv_prefix):
        return self.blocks_json

    def groups_from_json(self, js, groups):
        pass
