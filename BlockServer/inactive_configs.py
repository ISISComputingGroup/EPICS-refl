from config.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY
from inactive_config_server import InactiveConfigServerManager
from server_common.utilities import compress_and_hex
import os
import json
import re


class InactiveConfigManager(object):
    """ Class to handle data on all available configurations and manage their associated PVs"""
    def __init__(self, config_folder, macros, server, test_mode=False):
        self._configserver = InactiveConfigServerManager(config_folder, macros, test_mode=test_mode)
        self._config_metas = dict()
        self._subconfig_metas = dict()
        self._ca_server = server

        self._conf_path = os.path.abspath(config_folder + CONFIG_DIRECTORY)
        self._comp_path = os.path.abspath(config_folder + COMPONENT_DIRECTORY)

        self._import_configs()

    def get_config_names(self):
        return self._get_file_list(os.path.abspath(self._conf_path))

    def get_subconfig_names(self):
        return self._get_file_list(os.path.abspath(self._comp_path))

    def _get_file_list(self, path):
        files = []
        if os.path.isdir(path):
            files = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return files

    def get_configs_json(self):
        configs_string = list()
        for config in self._config_metas.values():
            configs_string.append(config.to_dict())
        return json.dumps(configs_string).encode('ascii', 'replace')

    def get_subconfigs_json(self):
        configs_string = list()
        for config in self._subconfig_metas.values():
            configs_string.append(config.to_dict())
        return json.dumps(configs_string).encode('ascii', 'replace')

    def _create_config_pv_name(self, name):
        if name not in self._config_metas:
            pv = self._create_pv_name(name)
            meta = self._configserver.get_config_meta()
            meta.pv = pv
            self._config_metas[name] = meta

    def _create_subconfig_pv_name(self, name):
        if name not in self._subconfig_metas:
            pv = self._create_pv_name(name, True)
            meta = self._configserver.get_config_meta()
            meta.pv = pv
            self._subconfig_metas[name] = meta

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
        # Creates the pvs and gets meta data
        for config in self.get_config_names():
            self.update_config_from_file(config)
        for comp in self.get_subconfig_names():
            self.update_comp_from_file(comp)

    def update_config_from_file(self, config):
        # Updates pvs with new data (creates them if not already made)
        config_data = self._get_saved_config_json(config, False)
        self._create_config_pv_name(config)
        self._ca_server.updatePV(self._config_metas[config].pv + ":GET_CONFIG_DETAILS", compress_and_hex(config_data))

    def update_comp_from_file(self, comp):
        # Updates pvs with new data (creates them if not already made)
        comp_data = self._get_saved_config_json(comp, True)
        self._create_subconfig_pv_name(comp)
        self._ca_server.updatePV(self._subconfig_metas[comp].pv + ":GET_COMPONENT_DETAILS", compress_and_hex(comp_data))

    def _get_saved_config_json(self, config, is_subconfig=False):
        self._configserver.load_config(config, is_subconfig)
        return self._configserver.get_config_details_json()

    def update_config_from_json(self, data):
        self._configserver.set_config_details(data)
        self._configserver.save_config()
        name = self._configserver.get_config_name()
        self._create_config_pv_name(name)
        self._ca_server.updatePV(self._config_metas[name].pv + ":GET_CONFIG_DETAILS", compress_and_hex(data))

    def update_subconfig_from_json(self, data):
        self._configserver.set_config_details(data)
        self._configserver.save_as_subconfig()
        name = self._configserver.get_config_name()
        self._create_subconfig_pv_name(name)
        self._ca_server.updatePV(self._subconfig_metas[name].pv + ":GET_COMPONENT_DETAILS", compress_and_hex(data))
