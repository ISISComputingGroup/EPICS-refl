import os
import json
import re
from threading import RLock

from BlockServer.core.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY, DEFAULT_COMPONENT
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from BlockServer.core.macros import MACROS
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from server_common.utilities import print_and_log, compress_and_hex
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker


GET_CONFIG_PV = ":GET_CONFIG_DETAILS"
GET_SUBCONFIG_PV = ":GET_COMPONENT_DETAILS"
DEPENDENCIES_PV = ":DEPENDENCIES"
CONFIG_CHANGED_PV = ":CURR_CONFIG_CHANGED"


class InvalidDeleteException(Exception):
    def __init__(self, value):
        super(InvalidDeleteException, self).__init__()
        self._value = value

    def __str__(self):
        return self._value


class ConfigListManager(object):
    """ Class to handle data on all available configurations and manage their associated PVs"""
    def __init__(self, block_server, config_folder, server, schema_folder, test_mode=False):
        self._config_metas = dict()
        self._subconfig_metas = dict()
        self._comp_dependecncies = dict()
        self._ca_server = server
        self._config_folder = config_folder
        self._test_mode = test_mode
        self._block_server = block_server  # Referencing a higher level object == bad
        self.active_config_name = ""
        self.active_components = []
        self._active_changed = False
        self.lock = RLock()

        self._conf_path = os.path.abspath(config_folder + CONFIG_DIRECTORY)
        self._comp_path = os.path.abspath(config_folder + COMPONENT_DIRECTORY)

        self._import_configs(schema_folder)

        # Create the changed PV
        self.set_active_changed(False)

    def get_active_changed(self):
        with self.lock:
            if self._active_changed:
                return 1
            else:
                return 0

    def set_active_changed(self, value):
        self._active_changed = value
        self._ca_server.updatePV(CONFIG_CHANGED_PV, self.get_active_changed())

    def _get_config_names(self):
        return self._get_file_list(os.path.abspath(self._conf_path))

    def _get_subconfig_names(self):
        sub_conf_list = self._get_file_list(os.path.abspath(self._comp_path))
        l = list()
        for cn in sub_conf_list:
            l.append(cn)
        return l

    def _get_file_list(self, path):
        files = []
        if os.path.isdir(path):
            files = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return files

    def get_configs(self):
        configs_string = list()
        for config in self._config_metas.values():
            configs_string.append(config.to_dict())
        return configs_string

    def get_subconfigs(self):
        subconfigs_string = list()
        for cn, cv in self._subconfig_metas.iteritems():
            if cn.lower() != DEFAULT_COMPONENT.lower():
                subconfigs_string.append(cv.to_dict())
        return subconfigs_string

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

    def _import_configs(self, schema_folder):
        # Create the pvs and get meta data
        config_list = self._get_config_names()
        subconfig_list = self._get_subconfig_names()

        # Must load components first for them all to be known in dependencies
        for comp_name in subconfig_list:
            try:
                ConfigurationSchemaChecker.check_config_file_matches_schema(schema_folder, self._comp_path + '\\' + comp_name + '\\'
                                                                , True)
            except Exception as err:
                print_and_log(str(err), "INFO")
            config = self.load_config(comp_name, True)
            self.update_a_config_in_list(config, True)

        # Create default if it does not exist
        if DEFAULT_COMPONENT.lower() not in subconfig_list:
            ConfigurationFileManager.copy_default(self._comp_path)

        for config_name in config_list:
            try:
                ConfigurationSchemaChecker.check_config_file_matches_schema(schema_folder, self._conf_path + '\\' + config_name
                                                                + '\\')
            except Exception as err:
                print_and_log(str(err), "INFO")
            config = self.load_config(config_name)
            self.update_a_config_in_list(config)

        # Add fileIO to version control
        if not self._test_mode:
            ConfigurationFileManager.add_configs_to_version_control(
                self._conf_path, config_list, "Blockserver started: all configs updated")

            ConfigurationFileManager.add_configs_to_version_control(
                self._comp_path, subconfig_list, "Blockserver started: all subconfigs updated")

    def load_config(self, name, is_subconfig=False):
        config = InactiveConfigHolder(self._config_folder, MACROS)
        config.load_inactive(name, is_subconfig)
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
        self._ca_server.updatePV(self._config_metas[name].pv + GET_CONFIG_PV, compress_and_hex(json.dumps(data)))

    def _update_subconfig_pv(self, name, data):
        # Updates pvs with new data
        self._ca_server.updatePV(self._subconfig_metas[name].pv + GET_SUBCONFIG_PV, compress_and_hex(json.dumps(data)))

    def update_a_config_in_list_filewatcher(self, config, is_subconfig=False):
        with self.lock:
            # Update dynamic PVs
            self.update_a_config_in_list(config, is_subconfig)

            # Update static PVs (some of these aren't completely necessary)
            if is_subconfig:
                self._block_server.update_comp_monitor()
                if config.get_config_name().lower() in [x.lower() for x in self.active_components]:
                    print_and_log("Active component edited in filesystem, reload to receive changes",
                                  src="FILEWTCHR")
                    self.set_active_changed(True)
            else:
                self._block_server.update_config_monitors()
                if config.get_config_name().lower() == self.active_config_name.lower():
                    print_and_log("Active config edited in filesystem, reload to receive changes",
                                  src="FILEWTCHR")
                    self.set_active_changed(True)

    def update_a_config_in_list(self, config, is_subconfig=False):
        """ Takes a ConfigServerManager object and updates the list of meta data and the individual PVs """
        name = config.get_config_name().lower()

        # Get pv name (create if doesn't exist)
        pv_name = self._get_pv_name(name, is_subconfig)

        # Get meta data from config
        meta = config.get_config_meta()
        meta.pv = pv_name

        # Add metas and update pvs appropriately
        if is_subconfig:
            if name is not DEFAULT_COMPONENT.lower():
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
            comps = config.get_component_names()
            for comp in comps:
                if comp in self._comp_dependecncies:
                    self._comp_dependecncies[comp].append(name)
                else:
                    self._comp_dependecncies[comp] = [name]
                self._update_subconfig_dependencies_pv(comp)

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

    def update_version_control_post_delete(self, folder, files):
        if not self._test_mode:
            ConfigurationFileManager.delete_configs_from_version_control(folder, files,
                                                                         "Deleted: " + ', '.join(list(files)))
        else:
            ConfigurationFileManager.delete_configs(folder, files)

    def delete_configs(self, delete_list, are_subconfigs=False):
        """ Takes a list of configs and removes them from the file system and any relevant PVs."""
        with self.lock:
            # TODO: clean this up?
            if not self._test_mode:
                print_and_log("Deleting: " + ', '.join(list(delete_list)), "INFO")
            delete_list = set([x.lower() for x in delete_list])
            if not are_subconfigs:
                if self.active_config_name.lower() in delete_list:
                    raise InvalidDeleteException("Cannot delete currently active configuration")
                if not delete_list.issubset(self._config_metas.keys()):
                    raise InvalidDeleteException("Delete list contains unknown configurations")
                for config in delete_list:
                    self._ca_server.deletePV(self._config_metas[config].pv + GET_CONFIG_PV)
                    del self._config_metas[config]
                    self._remove_config_from_dependencies(config)
                self.update_version_control_post_delete(self._conf_path, delete_list)
            else:
                if DEFAULT_COMPONENT.lower() in delete_list:
                    raise InvalidDeleteException("Cannot delete default component")
                # Only allow comps to be deleted if they appear in no configs
                for comp in delete_list:
                    if self._comp_dependecncies.get(comp):
                        raise InvalidDeleteException(comp + " is in use in: " + ', '.join(self._comp_dependecncies[comp]))
                if not delete_list.issubset(self._subconfig_metas.keys()):
                    raise InvalidDeleteException("Delete list contains unknown components")
                for comp in delete_list:
                    self._ca_server.deletePV(self._subconfig_metas[comp].pv + GET_SUBCONFIG_PV)
                    self._ca_server.deletePV(self._subconfig_metas[comp].pv + DEPENDENCIES_PV)
                    del self._subconfig_metas[comp]
                self.update_version_control_post_delete(self._comp_path, delete_list)

    def get_dependencies(self, comp_name):
        with self.lock:
            dependencies = self._comp_dependecncies.get(comp_name)
            if dependencies is None:
                return []
            else:
                return dependencies