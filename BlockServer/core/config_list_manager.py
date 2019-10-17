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
import json
import six
from threading import RLock

from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.core.macros import MACROS
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.core.config_list_manager_exceptions import InvalidDeleteException
from server_common.channel_access import verify_manager_mode, ChannelAccess

from server_common.utilities import print_and_log, compress_and_hex, create_pv_name, convert_to_json, \
    lowercase_and_make_unique
from server_common.common_exceptions import MaxAttemptsExceededException
from server_common.pv_names import BlockserverPVNames


def needs_lock(func):
    """
    Decorator which takes out the config list manager lock while the decorated function is running.
    """
    @six.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)
    return wrapper


def update_monitors_when_finished(func):
    """
    Decorator which updates monitors once the decorated function has finished running.
    """
    @six.wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.update_monitors()
        return result
    return wrapper


def deletion_context(func):
    return needs_lock(update_monitors_when_finished(func))


class ConfigListManager(object):
    """ Class to handle data on all available configurations and manage their associated PVs.

    Attributes:
        active_config_name (string): The name of the active configuration
        active_components (list): The names of the components in the active configuration
    """
    def __init__(self, block_server, schema_folder, file_manager, channel_access=ChannelAccess()):
        """Constructor.

        Args:
            block_server (block_server.BlockServer): A reference to the BlockServer itself
            schema_folder (string): The location of the schemas for validation
            file_manager (ConfigurationFileManager): Deals with writing the config files
        """

        self._config_metas = dict()
        self._component_metas = dict()
        self._comp_dependencies = dict()
        self._bs = block_server
        self.active_config_name = ""
        self.active_components = []
        self.all_components = dict()
        self._lock = RLock()
        self.channel_access = channel_access
        self.schema_folder = schema_folder
        self.file_manager = file_manager

        self._conf_path = FILEPATH_MANAGER.config_dir
        self._comp_path = FILEPATH_MANAGER.component_dir
        self._import_configs(self.schema_folder)

    def _update_pv_value(self, fullname, data):
        # First check PV exists if not create it
        if not self._bs.does_pv_exist(fullname):
            self._bs.add_string_pv_to_db(fullname, 16000)

        self._bs.setParam(fullname, data)
        self._bs.updatePVs()

    def _delete_pv(self, fullname):
        self._bs.delete_pv_from_db(fullname)

    def _get_config_names(self):
        return self._get_file_list(os.path.abspath(self._conf_path))

    def _get_component_names(self):
        comp_list = self._get_file_list(os.path.abspath(self._comp_path))
        return [component_name for component_name in comp_list]

    def _get_file_list(self, path):
        return self.file_manager.get_files_in_directory(path)

    def get_configs(self):
        """Returns all of the valid configurations, made up of those found on startup and those subsequently created.

        Returns:
            list : A list of available configurations
        """
        configs_string = list()
        for config in self._config_metas.values():
            configs_string.append(config.to_dict())
        return configs_string

    def get_components(self):
        """Returns all of the valid components, made up of those found on startup and those subsequently created.

        Returns:
            list : A list of available components
        """
        comps = list()
        for cn, cv in six.iteritems(self._component_metas):
            if cn.lower() != DEFAULT_COMPONENT.lower():
                comps.append(cv.to_dict())
        return comps

    def _import_configs(self, schema_folder):
        # Create the pvs and get meta data
        config_list = self._get_config_names()
        comp_list = self._get_component_names()

        # Must load components first for them all to be known in dependencies
        for comp_name in comp_list:
            try:
                path = FILEPATH_MANAGER.get_component_path(comp_name)
                # load_config checks the schema
                config = self.load_config(comp_name, True)
                self.update_a_config_in_list(config, True)
            except Exception as err:
                print_and_log("Error in loading component: %s" % err, "MINOR")

        # Create default if it does not exist
        if DEFAULT_COMPONENT.lower() not in comp_list:
            self.file_manager.copy_default(self._comp_path)

        for config_name in config_list:
            try:
                # load_config checks the schema
                config = self.load_config(config_name)
                self.update_a_config_in_list(config)
            except Exception as err:
                print_and_log("Error in loading config: %s" % err, "MINOR")

    def load_config(self, name, is_component=False):
        """Loads an inactive configuration or component.

        Args:
            name (string): The name of the configuration to load
            is_component (bool): Whether it is a component or not

        Returns:
            InactiveConfigHolder : The holder for the requested configuration
        """
        config = InactiveConfigHolder(MACROS, self.file_manager)
        config.load_inactive(name, is_component)
        return config

    def _update_component_dependencies_pv(self, name):
        # Updates PV with list of configs that depend on a component
        configs = []
        if name in self._comp_dependencies.keys():
            configs = self._comp_dependencies[name]
        if name in self._component_metas.keys():
            # Check just in case component failed to load
            pv_name = BlockserverPVNames.get_dependencies_pv(self._component_metas[name].pv)
            self._update_pv_value(pv_name, compress_and_hex(json.dumps(configs)))

    def _update_config_pv(self, name, data):
        # Updates pvs with new data
        pv_name = BlockserverPVNames.get_config_details_pv(self._config_metas[name].pv)
        self._update_pv_value(pv_name, compress_and_hex(json.dumps(data)))

    def _update_component_pv(self, name, data):
        # Updates pvs with new data
        pv_name = BlockserverPVNames.get_component_details_pv(self._component_metas[name].pv)
        self._update_pv_value(pv_name, compress_and_hex(json.dumps(data)))

    @needs_lock
    def update(self, config, is_component=False):
        """Updates the PVs associated with a configuration

        Args:
            config (ConfigHolder): The configuration holder
            is_component (bool): Whether it is a component or not
        """
        # Update dynamic PVs
        self.update_a_config_in_list(config, is_component)

        # Update static PVs (some of these aren't completely necessary)
        self.update_monitors()
        if is_component:
            if config.get_config_name().lower() in [x.lower() for x in self.active_components]:
                print_and_log("Active component edited in filesystem, reloading to get changes",
                              src="FILEWTCHR")
                self._bs.load_last_config()
        else:
            if config.get_config_name().lower() == self.active_config_name.lower():
                print_and_log("Active config edited in filesystem, reload to receive changes",
                              src="FILEWTCHR")

    @update_monitors_when_finished
    def update_a_config_in_list(self, config, is_component=False):
        """Takes a ConfigServerManager object and updates the list of meta data and the individual PVs.

        Args:
            config (ConfigHolder): The configuration holder
            is_component (bool): Whether it is a component or not
        """
        name = config.get_config_name()
        name_lower = name.lower()

        # Get pv name (create if doesn't exist)
        pv_name = self._get_pv_name(name_lower, is_component)

        # Get meta data from config
        meta = config.get_config_meta()
        meta.pv = pv_name

        # Add metas and update pvs appropriately
        if is_component:
            if name_lower != DEFAULT_COMPONENT.lower():
                self._component_metas[name_lower] = meta
                self._update_component_pv(name_lower, config.get_config_details())
                self._update_component_dependencies_pv(name_lower)
                self.all_components[name_lower] = config.get_config_details()
        else:
            if name_lower in self._config_metas.keys():
                # Config already exists
                self._remove_config_from_dependencies(name)

            self._config_metas[name_lower] = meta
            self._update_config_pv(name_lower, config.get_config_details())

            # Update component dependencies
            comps = config.get_component_names()
            for comp in comps:
                if comp.lower() in self._comp_dependencies:
                    self._comp_dependencies[comp.lower()].append(config.get_config_name())
                else:
                    self._comp_dependencies[comp.lower()] = [config.get_config_name()]
                self._update_component_dependencies_pv(comp.lower())

    def _remove_config_from_dependencies(self, config):
        # Remove old config from dependencies list
        for comp, confs in six.iteritems(self._comp_dependencies):
            if config in confs:
                self._comp_dependencies[comp.lower()].remove(config)
                self._update_component_dependencies_pv(comp.lower())

    def _get_pv_name(self, config_name, is_component=False):
        """Returns the name of the pv corresponding to config_name, this name is generated if not already created."""
        if not is_component:
            if config_name in self._config_metas:
                pv_name = self._config_metas[config_name].pv
            else:
                curr_pvs = [meta.pv for meta in self._config_metas.values()]
                pv_name = create_pv_name(config_name, curr_pvs, "CONFIG")
        else:
            if config_name in self._component_metas:
                pv_name = self._component_metas[config_name].pv
            else:
                curr_pvs = [meta.pv for meta in self._component_metas.values()]
                pv_name = create_pv_name(config_name, curr_pvs, "COMPONENT")
        return pv_name

    @deletion_context
    def delete_configs(self, delete_list):
        print_and_log("Deleting configurations: {}".format(', '.join(list(delete_list)), "INFO"))
        lower_delete_list = lowercase_and_make_unique(delete_list)

        if self.active_config_name.lower() in lower_delete_list:
            raise InvalidDeleteException("Cannot delete currently active configuration")
        if not lower_delete_list.issubset(self._config_metas.keys()):
            raise InvalidDeleteException("Delete list contains unknown configurations")

        for config in lower_delete_list:
            if self._config_metas[config].isProtected:
                verify_manager_mode(self.channel_access,
                                    message="Attempting to delete protected configuration ('{}')".format(config))

        for config in delete_list:
            self._delete_single_config(config)

    def _delete_single_config(self, config):
        try:
            self.file_manager.delete(config, is_component=False)
        except MaxAttemptsExceededException:
            print_and_log("Could not delete configuration {name} from file system. "
                          "Make sure its files are not in use by a different process.".format(name=config),
                          "MINOR")

        self._delete_pv(BlockserverPVNames.get_config_details_pv(self._config_metas[config.lower()].pv))
        del self._config_metas[config.lower()]
        self._remove_config_from_dependencies(config)

    @deletion_context
    def delete_components(self, delete_list):
        print_and_log("Deleting components: {}".format(', '.join(list(delete_list)), "INFO"))
        lower_delete_list = lowercase_and_make_unique(delete_list)

        if DEFAULT_COMPONENT.lower() in lower_delete_list:
            raise InvalidDeleteException("Cannot delete default component")

        # Only allow comps to be deleted if they appear in no configs
        for component in lower_delete_list:
            if self._comp_dependencies.get(component):
                raise InvalidDeleteException(
                    "{} is in use in: {}".format(component, ', '.join(self._comp_dependencies[component])))

        if not lower_delete_list.issubset(self._component_metas.keys()):
            raise InvalidDeleteException("Delete list contains unknown components")

        for component in lower_delete_list:
            if self._component_metas[component].isProtected:
                verify_manager_mode(self.channel_access,
                                    message="Attempting to delete protected component ('{}')".format(component))

        for component in delete_list:
            self._delete_single_component(component)

    def _delete_single_component(self, component):
        try:
            self.file_manager.delete(component, is_component=True)
        except MaxAttemptsExceededException:
            print_and_log("Could not delete component {name} from file system. "
                          "Make sure its files are not in use by a different process.".format(name=component),
                          "MINOR")
        self._delete_pv(BlockserverPVNames.get_component_details_pv(self._component_metas[component].pv))
        self._delete_pv(BlockserverPVNames.get_dependencies_pv(self._component_metas[component].pv))
        del self._component_metas[component]
        del self.all_components[component]

    @needs_lock
    def get_dependencies(self, comp_name):
        """Get the names of any configurations that depend on this component.

        Args:
            comp_name (string): The name of the component

        Returns:
            list : The configurations that depend on the component
        """
        dependencies = self._comp_dependencies.get(comp_name.lower())
        return [] if dependencies is None else dependencies

    def update_monitors(self):
        with self._bs.monitor_lock:
            print_and_log("Updating config list monitors")
            # Set the available configs
            self._bs.setParam(BlockserverPVNames.CONFIGS, compress_and_hex(convert_to_json(self.get_configs())))
            # Set the available comps
            self._bs.setParam(BlockserverPVNames.COMPS, compress_and_hex(convert_to_json(self.get_components())))
            # Set the available component details
            self._bs.setParam(BlockserverPVNames.ALL_COMPONENT_DETAILS,
                              compress_and_hex(convert_to_json(self.all_components.values())))
            # Update them
            self._bs.updatePVs()
