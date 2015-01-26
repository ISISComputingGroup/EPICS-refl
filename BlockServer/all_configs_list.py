from config.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY
from config.file_manager import ConfigurationFileManager
from macros import MACROS
from config_server import ConfigServerManager
from server_common.utilities import print_and_log, compress_and_hex
import os
import json
import re

GET_CONFIG_PV = ":GET_CONFIG_DETAILS"
GET_SUBCONFIG_PV = ":GET_COMPONENT_DETAILS"
DEPENDENCIES_PV = ":DEPENDENCIES"


class ConfigListManager(object):
    """ Class to handle data on all available configurations and manage their associated PVs"""
    def __init__(self, config_folder, server, test_mode=False):
        self._config_metas = dict()
        self._subconfig_metas = dict()
        self._comp_dependecncies = dict()
        self._ca_server = server
        self._config_folder = config_folder
        self._test_mode = test_mode

        self._conf_path = os.path.abspath(config_folder + CONFIG_DIRECTORY)
        self._comp_path = os.path.abspath(config_folder + COMPONENT_DIRECTORY)

        self._import_configs()

    def _get_config_names(self):
        return self._get_file_list(os.path.abspath(self._conf_path))

    def _get_subconfig_names(self):
        return self._get_file_list(os.path.abspath(self._comp_path))

    def _get_file_list(self, path):
        files = []
        if os.path.isdir(path):
            files = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return files

    def get_configs_json(self):
        configs_string = list()
        self._update_whole_config_list()
        for config in self._config_metas.values():
            configs_string.append(config.to_dict())
        return json.dumps(configs_string).encode('ascii', 'replace')

    def get_subconfigs_json(self):
        configs_string = list()
        self._update_whole_config_list(True)
        for config in self._subconfig_metas.values():
            configs_string.append(config.to_dict())
        return json.dumps(configs_string).encode('ascii', 'replace')

    def _create_pv_name(self, config_name, is_subconfig=False):
        pv_text = config_name.upper().replace(" ", "_")
        pv_text = re.sub(r'\W', '', pv_text)
        # Check some edge cases of unreasonable names
        if re.search(r"[^0-9_]", pv_text) is None or pv_text == '':
            pv_text = "CONFIG"

        # Make sure PVs are unique
        i = 0
        pv = pv_text

        if is_subconfig:
            curr_pvs = [meta.pv for meta in self._subconfig_metas.values()]
        else:
            curr_pvs = [meta.pv for meta in self._config_metas.values()]

        while pv in curr_pvs:
            pv = pv_text + str(i)
            i += 1

        return pv

    def _import_configs(self):
        # Create the pvs and get meta data
        config_list = self._get_config_names()
        subconfig_list = self._get_subconfig_names()

        # Must load components first for them all to be known in dependencies
        for comp_name in subconfig_list:
            config = self._load_config(comp_name, True)
            self.update_a_config_in_list(config, True)

        for config_name in config_list:
            config = self._load_config(config_name)
            self.update_a_config_in_list(config)

        # Add files to version control
        if not self._test_mode:
            ConfigurationFileManager.add_configs_to_version_control(
                self._conf_path, config_list, "Blockserver started: all configs updated")

            ConfigurationFileManager.add_configs_to_version_control(
                self._comp_path, subconfig_list, "Blockserver started: all subconfigs updated")

    def _load_config(self, name, is_subconfig=False):
        config = ConfigServerManager(self._config_folder, MACROS)
        config.load_config(json.dumps(name), is_subconfig)
        return config

    def _update_subconfig_dependencies_pv(self, name):
        # Updates PV with list of configs that depend on a subconfig
        configs = []
        if name in self._comp_dependecncies.keys():
            configs = self._comp_dependecncies[name]
        self._ca_server.updatePV(self._subconfig_metas[name].pv + DEPENDENCIES_PV,
                                 compress_and_hex(json.dumps(configs)))

    def _update_config_pv(self, name, data):
        # Updates pvs with new data
        self._ca_server.updatePV(self._config_metas[name].pv + GET_CONFIG_PV, compress_and_hex(data))

    def _update_subconfig_pv(self, name, data):
        # Updates pvs with new data
        self._ca_server.updatePV(self._subconfig_metas[name].pv + GET_SUBCONFIG_PV, compress_and_hex(data))

    def update_a_config_in_list(self, config, is_subconfig=False):
        """Takes a ConfigServerManager object and updates the list of meta data and the individual PVs"""
        name = config.get_config_name().lower()

        # Get pv name (create if doesn't exist)
        pv_name = self._get_pv_name(name, is_subconfig)

        # Get meta data from config
        meta = config.get_config_meta()
        meta.pv = pv_name

        # Add metas and update pvs appropriately
        if is_subconfig:
            self._subconfig_metas[name] = meta
            self._update_subconfig_pv(name, config.get_config_details())
            self._update_subconfig_dependencies_pv(name)
        else:
            if name in self._config_metas.keys():
                # Config already exists
                self._remove_config_from_dependencies(name)

            self._config_metas[name] = meta
            self._update_config_pv(name, config.get_config_details())

            # Update component dependencies
            comps = config.get_conf_subconfigs()
            for comp in comps:
                if comp in self._comp_dependecncies:
                    self._comp_dependecncies[comp].append(name)
                else:
                    self._comp_dependecncies[comp] = [name]
                self._update_subconfig_dependencies_pv(comp)

    def _update_whole_config_list(self, is_subconfig=False):
        # This method is only required as there is no filewatcher
        if not is_subconfig:
            name_list = self._get_config_names()
            for config_name in name_list:
                self.update_a_config_in_list(self._load_config(config_name))
        else:
            name_list = self._get_subconfig_names()
            for subconfig_name in name_list:
                self.update_a_config_in_list(self._load_config(subconfig_name, True), True)

    def _remove_config_from_dependencies(self, config):
        # Remove old config from dependencies list
        for comp, confs in self._comp_dependecncies.iteritems():
            if config in confs:
                self._comp_dependecncies[comp].remove(config)
                self._update_subconfig_dependencies_pv(comp)

    def _get_pv_name(self, config_name, is_subconfig=False):
        """Returns the name of the pv corresponding to config_name, this name is generated if not already created"""
        if not is_subconfig:
            if config_name in self._config_metas:
                pv_name = self._config_metas[config_name].pv
            else:
                pv_name = self._create_pv_name(config_name, False)
        else:
            if config_name in self._subconfig_metas:
                pv_name = self._subconfig_metas[config_name].pv
            else:
                pv_name = self._create_pv_name(config_name, True)
        return pv_name

    def update_version_control_pre_delete(self, folder, files):
        if not self._test_mode:
            ConfigurationFileManager.add_configs_to_version_control(folder, files,
                                    "Updating version control prior to deleting: " + ', '.join(list(files)))

    def update_version_control_post_delete(self, folder, files):
        if not self._test_mode:
            ConfigurationFileManager.delete_configs_from_version_control(folder, files,
                                                                         "Deleted: " + ', '.join(list(files)))
        else:
            ConfigurationFileManager.delete_configs(folder, files)

    def delete_configs(self, json_configs, active_config, are_subconfigs=False):
        """Takes a json list of configs and removes them from the file system and any relevant pvs.
           The method also requires the active config object to check against"""
        # TODO: clean this up!
        delete_list = json.loads(json_configs)
        if not self._test_mode:
            print_and_log("Deleting: " + ', '.join(list(delete_list)), "INFO")
        delete_list = set([x.lower() for x in delete_list])
        if not are_subconfigs:
            if active_config.get_config_name() in delete_list:
                raise Exception("Cannot delete currently active configuration")
            self.update_version_control_pre_delete(self._conf_path, delete_list)
            if not delete_list.issubset(self._config_metas.keys()):
                raise Exception("Delete list contains unknown configurations")
            for config in delete_list:
                self._ca_server.deletePV(self._config_metas[config].pv + GET_CONFIG_PV)
                del self._config_metas[config]
                self._remove_config_from_dependencies(config)
            self.update_version_control_post_delete(self._conf_path, delete_list)
        else:
            # Only allow comps to be deleted if they appear in no configs
            for comp in delete_list:
                if self._comp_dependecncies.get(comp):
                    raise Exception(comp + " is in use in: " + ', '.join(self._comp_dependecncies[comp]))
            self.update_version_control_pre_delete(self._comp_path, delete_list)
            if not delete_list.issubset(self._subconfig_metas.keys()):
                raise Exception("Delete list contains unknown components")
            for comp in delete_list:
                self._ca_server.deletePV(self._subconfig_metas[comp].pv + GET_SUBCONFIG_PV)
                self._ca_server.deletePV(self._subconfig_metas[comp].pv + DEPENDENCIES_PV)
                del self._subconfig_metas[comp]
            self.update_version_control_post_delete(self._comp_path, delete_list)