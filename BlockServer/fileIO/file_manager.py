import os
import shutil
from collections import OrderedDict

from server_common.utilities import parse_xml_removing_namespace, print_and_log
from BlockServer.config.containers import Group
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.config.configuration import Configuration, MetaData
from config_version_control import ConfigVersionControl
from vc_exceptions import NotUnderVersionControl
from BlockServer.core.constants import FILENAME_BLOCKS, FILENAME_GROUPS, FILENAME_IOCS, FILENAME_SUBCONFIGS, FILENAME_META
from BlockServer.core.constants import GRP_NONE, DEFAULT_COMPONENT, EXAMPLE_DEFAULT


class ConfigurationFileManager(object):
    """ The ConfigurationFileManager class.

    Contains utilities to save and load configurations and to communicate with the version control system.
    """

    @staticmethod
    def find_ci(root_path, name):
        """find a file with a case insensitive match"""
        res = ''
        for f in os.listdir(root_path):
            if (f.lower() == name.lower()):
                res = f
        return res
    
    @staticmethod
    def load_config(root_path, config_name, macros):
        """Loads the configuration from the specified folder.

        Args:
            root_path (string) : The root folder for all configurations
            config_name (string) : The name of the configuration
            macros (dict) : The BlockServer macros
        """
        configuration = Configuration(macros)
        # we need to do a case insensitive file system match
        cn = ConfigurationFileManager.find_ci(root_path, config_name)
        if not cn:
            raise IOError("Configuration could not be found: " + config_name)
        config_folder = os.path.abspath(os.path.join(root_path, cn))
        path = os.path.abspath(config_folder)
        if not os.path.isdir(path):
            raise IOError("Configuration could not be found: " + config_name)

        # Create empty containers
        blocks = OrderedDict()
        groups = OrderedDict()
        subconfigs = OrderedDict()
        iocs = OrderedDict()

        # Make sure NONE group exists
        groups[GRP_NONE.lower()] = Group(GRP_NONE)

        # Open the block file first
        blocks_path = path + "/" + FILENAME_BLOCKS
        if os.path.isfile(blocks_path):
            root = parse_xml_removing_namespace(blocks_path)
            ConfigurationXmlConverter.blocks_from_xml(root, blocks, groups)

        # Import the groups
        groups_path = path + "/" + FILENAME_GROUPS
        if os.path.isfile(groups_path):
            root = parse_xml_removing_namespace(groups_path)
            ConfigurationXmlConverter.groups_from_xml(root, groups, blocks)

        # Import the IOCs
        iocs_path = path + "/" + FILENAME_IOCS
        if os.path.isfile(iocs_path):
            root = parse_xml_removing_namespace(iocs_path)
            ConfigurationXmlConverter.ioc_from_xml(root, iocs)

        # Import the subconfigs
        subconfig_path = path + "/" + FILENAME_SUBCONFIGS
        if os.path.isfile(subconfig_path):
            root = parse_xml_removing_namespace(subconfig_path)
            ConfigurationXmlConverter.subconfigs_from_xml(root, subconfigs)

        # Import the metadata
        meta = MetaData(config_name)
        meta_path = path + '/' + FILENAME_META
        if os.path.isfile(meta_path):
            root = parse_xml_removing_namespace(meta_path)
            ConfigurationXmlConverter.meta_from_xml(root, meta)

        # Set properties in the config
        configuration.blocks = blocks
        configuration.groups = groups
        configuration.iocs = iocs
        configuration.subconfigs = subconfigs
        configuration.meta = meta
        return configuration

    @staticmethod
    def save_config(configuration, root_path, config_name):
        """Saves the current configuration with the specified name.

        Args:
            configuration (Configuration) : The actual configuration to save
            root_path (string) : The root folder where configuration are stored
            config_name (string) : The configuration name to save under
        """
        config_folder = os.path.abspath(os.path.join(root_path, config_name))
        path = os.path.abspath(config_folder)
        if not os.path.isdir(path):
            # Create the directory
            os.makedirs(path)

        blocks_xml = ConfigurationXmlConverter.blocks_to_xml(configuration.blocks, configuration.macros)
        groups_xml = ConfigurationXmlConverter.groups_to_xml(configuration.groups)
        iocs_xml = ConfigurationXmlConverter.iocs_to_xml(configuration.iocs)
        meta_xml = ConfigurationXmlConverter.meta_to_xml(configuration.meta)
        try:
            subconfigs_xml = ConfigurationXmlConverter.subconfigs_to_xml(configuration.subconfigs)
        except:
            # Is a subconfig, so no subconfigs
            subconfigs_xml = ConfigurationXmlConverter.subconfigs_to_xml(dict())

        # Save blocks
        with open(path + '/' + FILENAME_BLOCKS, 'w') as f:
            f.write(blocks_xml)

        # Save groups
        with open(path + '/' + FILENAME_GROUPS, 'w') as f:
            f.write(groups_xml)

        # Save IOCs
        with open(path + '/' + FILENAME_IOCS, 'w') as f:
            f.write(iocs_xml)

        # Save subconfigs
        with open(path + '/' + FILENAME_SUBCONFIGS, 'w') as f:
            f.write(subconfigs_xml)

        # Save meta
        with open(path + '/' + FILENAME_META, 'w') as f:
            f.write(meta_xml)

    @staticmethod
    def subconfig_exists(root_path, name):
        """Checks to see if a component exists.

        root_path (string) : The root folder where components are stored
        name (string) : The name of the components

        Raises:
            (Exception) : raises an Exception if the component does not exist
        """
        if not os.path.isdir(os.path.join(root_path, name)):
            raise Exception("Subconfig does not exist")

    @staticmethod
    def copy_default(dest_path):
        """Copies the default/base component in if it does exist.

        Args:
            dest_path (string) : The root folder where configurations are stored
        """
        shutil.copytree(os.path.abspath(os.path.join(os.environ["MYDIRBLOCK"], EXAMPLE_DEFAULT)),
                        os.path.join(dest_path,DEFAULT_COMPONENT))
