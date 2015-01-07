import os
from collections import OrderedDict
from server_common.utilities import parse_xml_removing_namespace, print_and_log

from BlockServer.config.containers import Group
from xml_converter import ConfigurationXmlConverter

from BlockServer.config.constants import GRP_NONE, AUTOSAVE_NAME
from BlockServer.config.configuration import Configuration, MetaData

from config_version_control import ConfigVersionControl, NotUnderVersionControl

FILENAME_BLOCKS = "blocks.xml"
FILENAME_GROUPS = "groups.xml"
FILENAME_IOCS = "iocs.xml"
FILENAME_SUBCONFIGS = "components.xml"
FILENAME_META = "meta.xml"

class ConfigurationFileManager(object):
    """Saves and loads configuration data from file"""
    @staticmethod
    def load_config(root_path, config_name, macros):
        """Loads the configuration from the specified folder"""
        configuration = Configuration(macros)
        config_folder = os.path.abspath(root_path) + "\\" + config_name
        path = os.path.abspath(config_folder)
        if not os.path.isdir(path):
            raise Exception("Configuration could not be found")

        # Create empty containers
        blocks = OrderedDict()
        groups = OrderedDict()
        subconfigs = OrderedDict()
        iocs = OrderedDict()

        #Make sure NONE group exists
        groups[GRP_NONE.lower()] = Group(GRP_NONE)

        #Open the block file first
        blocks_path = path + "/" + FILENAME_BLOCKS
        if os.path.isfile(blocks_path):
            root = parse_xml_removing_namespace(blocks_path)
            ConfigurationXmlConverter.blocks_from_xml(root, blocks, groups)

        #Import the groups
        groups_path = path + "/" + FILENAME_GROUPS
        if os.path.isfile(groups_path):
            root = parse_xml_removing_namespace(groups_path)
            ConfigurationXmlConverter.groups_from_xml(root, groups, blocks)

        #Import the IOCs
        iocs_path = path + "/" + FILENAME_IOCS
        if os.path.isfile(iocs_path):
            root = parse_xml_removing_namespace(iocs_path)
            ConfigurationXmlConverter.ioc_from_xml(root, iocs)

        #Import the subconfigs
        subconfig_path = path + "/" + FILENAME_SUBCONFIGS
        if os.path.isfile(subconfig_path):
            root = parse_xml_removing_namespace(subconfig_path)
            ConfigurationXmlConverter.subconfigs_from_xml(root, subconfigs)

        #Import the metadata
        meta = ConfigurationFileManager.load_meta_data(root_path, config_name)

        # Set properties in the config
        configuration.blocks = blocks
        configuration.groups = groups
        configuration.iocs = iocs
        configuration.subconfigs = subconfigs
        configuration.meta = meta
        return configuration


    @staticmethod
    def save_config(configuration, root_path, config_name, test_mode = False):
        """Saves the current configuration with the specified name"""
        config_folder = os.path.abspath(root_path) + "\\" + config_name
        path = os.path.abspath(config_folder)
        if not os.path.isdir(path):
            #create the directory
            os.makedirs(path)

        blocks_xml = ConfigurationXmlConverter.blocks_to_xml(configuration.blocks, configuration.macros)
        groups_xml = ConfigurationXmlConverter.groups_to_xml(configuration.groups)
        iocs_xml = ConfigurationXmlConverter.iocs_to_xml(configuration.iocs)
        meta_xml = ConfigurationXmlConverter.meta_to_xml(configuration.meta)
        try:
            subconfigs_xml = ConfigurationXmlConverter.subconfigs_to_xml(configuration.subconfigs)
        except:
            #Is a subconfig, so no subconfigs
            subconfigs_xml = ConfigurationXmlConverter.subconfigs_to_xml(dict())

        #Save blocks
        with open(path + '/' + FILENAME_BLOCKS, 'w') as f:
            f.write(blocks_xml)

        #Save groups
        with open(path + '/' + FILENAME_GROUPS, 'w') as f:
            f.write(groups_xml)

        #Save IOCs
        with open(path + '/' + FILENAME_IOCS, 'w') as f:
            f.write(iocs_xml)

        #Save subconfigs
        with open(path + '/' + FILENAME_SUBCONFIGS, 'w') as f:
            f.write(subconfigs_xml)

        #Save meta
        with open(path + '/' + FILENAME_META, 'w') as f:
            f.write(meta_xml)

        if not test_mode:
            ConfigurationFileManager.add_configs_to_version_control(root_path, config_name, config_name + " modified")

    @staticmethod
    def add_configs_to_version_control(root_path, config_name, commit_message):
        # Create version control manager
        try:
            vc = ConfigVersionControl(root_path)
        except NotUnderVersionControl as err:
            print_and_log(err, "INFO")
        except Exception as err:
            print_and_log("Error in applying version control: " + str(err), "ERROR")
        else:
            vc.add(root_path + '/' + config_name)
            vc.commit(commit_message)

    @staticmethod
    def subconfig_exists(root_path, name):
        print root_path
        if not os.path.isdir(root_path + '/' + name):
            raise Exception("Subconfig does not exist")

    @staticmethod
    def load_meta_data(root_path, config_name):
        meta = MetaData(config_name)
        meta_path = os.path.abspath(root_path) + "\\" + config_name + '/' + FILENAME_META
        if os.path.isfile(meta_path):
            root = parse_xml_removing_namespace(meta_path)
            ConfigurationXmlConverter.meta_from_xml(root, meta)
        return meta
