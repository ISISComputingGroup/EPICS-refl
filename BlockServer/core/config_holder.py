""" Contains the code for the ConfigHolder class"""
import os
import copy
import datetime
from collections import OrderedDict
import re

from BlockServer.fileIO.file_manager import ConfigurationFileManager
from BlockServer.config.configuration import Configuration
from BlockServer.core.constants import DEFAULT_COMPONENT, GRP_NONE
from BlockServer.config.group import Group
from BlockServer.core.macros import PVPREFIX_MACRO
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


class ConfigHolder(object):
    """ The ConfigHolder class.

    Holds a configuration which can then be manpulated via this class.
    """
    def __init__(self, macros, vc_manager, is_component=False, file_manager=ConfigurationFileManager(),
                 test_config=None):
        """ Constructor.

        Args:
            macros (dict): The dictionary containing the macros
            is_component (bool): Defines whether the configuration held is a component or not
            file_manager (ConfigurationFileManager): The object used to save the configuration
            test_config (Configuration): A dummy configuration used for the unit tests
        """
        if test_config is None:
            self._config = Configuration(macros)
        else:
            self._config = test_config
        self._components = OrderedDict()
        self._is_component = is_component
        self._macros = macros
        self._vc = vc_manager

        self._config_path = FILEPATH_MANAGER.config_dir
        self._component_path = FILEPATH_MANAGER.component_dir
        self._filemanager = file_manager

        self._cached_config = Configuration(macros)
        self._cached_components = OrderedDict()

    def clear_config(self):
        """ Clears the configuration.
        """
        self._config = Configuration(self._macros)
        self._components = OrderedDict()
        self._is_component = False

    def add_component(self, name, component):
        """ Add a component to the configuration.

        Args:
            name (string): The name of the component being added
            component (Component): The component object to be added
        """
        # Add it to the holder
        if self._is_component:
            raise Exception("Can not add a component to a component")

        if name.lower() not in self._components:
            # Add it
            component.set_name(name)
            self._components[name.lower()] = component
            self._config.components[name.lower()] = name  # Only needs its case sensitive name name
        else:
            raise Exception("Requested component is already part of the configuration: " + str(name))

    def remove_comp(self, name):
        """ Removes a component from the configuration.

        This is not needed as part of the BlockServer as such, but it helps with unit testing.

        Args:
            name (string): The name of the component to remove
        """
        # Remove it from the holder
        if self._is_component:
            raise Exception("Can not remove a component from a component")
        del self._components[name.lower()]
        del self._config.components[name.lower()]

    def get_blocknames(self):
        """ Get all the blocknames including those in the components.

        Returns:
            list : The names of all the blocks
        """
        names = list()
        for bn, bv in self._config.blocks.iteritems():
            names.append(bv.name)
        for cn, cv in self._components.iteritems():
            for bn, bv in cv.blocks.iteritems():
                # Ignore duplicates
                if bv.name not in names:
                    names.append(bv.name)
        return names

    def get_block_details(self):
        """ Get the configuration details for all the blocks including any in components.

        Returns:
            dict : A dictionary of block objects
        """
        blks = copy.deepcopy(self._config.blocks)
        for cn, cv in self._components.iteritems():
            for bn, bv in cv.blocks.iteritems():
                if bn not in blks:
                    blks[bn] = bv
        return blks

    def get_group_details(self):
        """ Get the groups details for all the groups including any in components.

        Returns:
            dict : A dictionary of group objects
        """
        blocks = self.get_blocknames()
        used_blocks = list()
        groups = copy.deepcopy(self._config.groups)
        for n, v in groups.iteritems():
            used_blocks.extend(v.blocks)
        for cn, cv in self._components.iteritems():
            for gn, grp in cv.groups.iteritems():
                if gn not in groups.keys():
                    # Add the groups if they have not been used before and exist
                    blks = [x for x in grp.blocks if x not in used_blocks and x in blocks]
                    if len(blks) > 0:
                        # Only add if contains blocks
                        groups[gn] = grp
                        groups[gn].blocks = blks
                        used_blocks.extend(blks)
                else:
                    # If group exists then append with component group
                    # But don't add any duplicate blocks or blocks that don't exist
                    for bn in grp.blocks:
                        if bn not in groups[gn].blocks and bn not in used_blocks and bn in blocks:
                            groups[gn].blocks.append(bn)
                            used_blocks.append(bn)
        return groups

    def _set_group_details(self, redefinition):
        # Any redefinition only affects the main configuration
        homeless_blocks = self.get_blocknames()
        for grp in redefinition:
            # Skip the NONE group
            if grp["name"].lower() == GRP_NONE.lower():
                continue
            # If the group is in the config then it can be changed completely
            if grp["name"].lower() in self._config.groups:
                if len(grp["blocks"]) == 0:
                    # No blocks so delete the group
                    del self._config.groups[grp["name"].lower()]
                    continue
                self._config.groups[grp["name"].lower()].blocks = []
                for blk in grp["blocks"]:
                    if blk in homeless_blocks:
                        self._config.groups[grp["name"].lower()].blocks.append(blk)
                        homeless_blocks.remove(blk)
            else:
                # Not in config yet, so add it (it will override settings in any components)
                # Only add it if there are actually blocks
                if len(grp["blocks"]) > 0:
                    self._config.groups[grp["name"].lower()] = Group(grp["name"])
                    for blk in grp["blocks"]:
                        if blk in homeless_blocks:
                            self._config.groups[grp["name"].lower()].blocks.append(blk)
                            homeless_blocks.remove(blk)
        # Finally, anything in homeless gets put in NONE
        if GRP_NONE.lower() not in self._config.groups:
            self._config.groups[GRP_NONE.lower()] = Group(GRP_NONE)
        self._config.groups[GRP_NONE.lower()].blocks = homeless_blocks

    def get_config_name(self):
        """ Get the name of the configuration.

        Returns:
            string : The name
        """
        return self._config.get_name()

    def _set_config_name(self, name):
        self._config.set_name(name)

    def get_ioc_names(self, include_base=False):
        """ Get the names of the IOCs in the configuration and any components.

        Args:
            include_base (bool, optional): Whether to include the IOCs in base

        Returns:
            list : The names of the IOCs
        """
        iocs = self._config.iocs.keys()
        for cn, cv in self._components.iteritems():
            if include_base:
                iocs.extend(cv.iocs)
            elif cn.lower() != DEFAULT_COMPONENT.lower():
                iocs.extend(cv.iocs)
        return iocs

    def get_ioc_details(self):
        """ Get the details of the IOCs in the configuration.

        Returns:
            dict : A copy of all the configuration IOC details
        """
        iocs = copy.deepcopy(self._config.iocs)
        return iocs

    def get_component_ioc_details(self):
        """ Get the details of the IOCs in any components.

        Returns:
            dict : A copy of all the component IOC details
        """
        iocs = {}
        for cn, cv in self._components.iteritems():
            for n, v in cv.iocs.iteritems():
                if n not in iocs:
                     iocs[n] = v
        return iocs

    def get_all_ioc_details(self):
        """  Ge the details of the IOCs in the configuration and any components.

        Returns:
            dict : A copy of all the IOC details
        """
        iocs = self.get_ioc_details()
        iocs.update(self.get_component_ioc_details())
        return iocs

    def get_component_names(self, include_base=False):
        """ Get the names of the components in the configuration.

        Args:
            include_base (bool, optional): Whether to include the base in the list of names

        Returns:
            list : A list of components in the configuration
        """
        l = list()
        for cn, cv in self._components.iteritems():
            if (include_base) or (cn.lower() != DEFAULT_COMPONENT.lower()):
                l.append(cv.get_name())
        return l

    def add_block(self, blockargs):
        """ Add a block to the configuration.

        Args:
            blockargs (dict): A dictionary of settings for the new block
        """
        self._config.add_block(**blockargs)

    def _add_ioc(self, name, component=None, autostart=True, restart=True, macros=None, pvs=None, pvsets=None,
                 simlevel=None):
        # TODO: use IOC object instead?
        if component is None:
            self._config.add_ioc(name, None, autostart, restart, macros, pvs, pvsets, simlevel)
        else:
            if component.lower() in self._components:
                self._components[component.lower()].add_ioc(name, component, autostart, restart, macros, pvs, pvsets,
                                                            simlevel)
            else:
                raise Exception("No component called %s" % component)

    def get_config_details(self):
        """ Get the details of the configuration.

        Returns:
            dict : A dictionary containing all the details of the configuration
        """
        config = dict()

        # Blocks, groups and IOC include the component ones
        config['blocks'] = self._blocks_to_list(True)
        config['groups'] = self._groups_to_list()
        config['iocs'] = self._iocs_to_list()
        config['component_iocs'] = self._iocs_to_list_with_components()
        # Just return the names of the components
        config['components'] = self._comps_to_list()
        config['name'] = self._config.get_name()
        config['description'] = self._config.meta.description
        config['synoptic'] = self._config.meta.synoptic
        config['history'] = self._config.meta.history

        return config

    def _comps_to_list(self):
        comps = list()
        for cn, cv in self._components.iteritems():
            if cn.lower() != DEFAULT_COMPONENT.lower():
                comps.append({'name': cv.get_name()})
        return comps

    def _blocks_to_list(self, expand_macro=False):
        blocks = self.get_block_details()
        blks = list()
        if blocks is not None:
            for block in blocks.values():
                b = block.to_dict()
                if expand_macro or b['local']:
                    # Replace the prefix
                    b['pv'] = b['pv'].replace(PVPREFIX_MACRO, self._macros[PVPREFIX_MACRO])
                blks.append(b)
        return blks

    def _groups_to_list(self):
        groups = self.get_group_details()
        grps = list()
        if groups is not None:
            for group in groups.values():
                if group.name.lower() != GRP_NONE.lower():
                    grps.append(group.to_dict())

            # Add NONE group at end
            if GRP_NONE.lower() in groups.keys():
                grps.append(groups[GRP_NONE.lower()].to_dict())
        return grps

    def _iocs_to_list(self):
        ioc_list = list()
        for n, ioc in self._config.iocs.iteritems():
            ioc_list.append(ioc.to_dict())

        return ioc_list

    def _iocs_to_list_with_components(self):
        ioc_list = self._iocs_to_list()

        for cn, cv in self._components.iteritems():
            for n, ioc in cv.iocs.iteritems():
                ioc_list.append(ioc.to_dict())
        return ioc_list

    def set_config_details(self, details):
        """ Set the details of the configuration from a dictionary.

        Args:
            details (dict): A dictionary containing the new configuration settings
        """
        self._cache_config()

        try:
            self.clear_config()
            if "iocs" in details:
                # List of dicts
                for ioc in details["iocs"]:
                    macros = self._to_dict(ioc.get('macros'))
                    pvs = self._to_dict(ioc.get('pvs'))
                    pvsets = self._to_dict(ioc.get('pvsets'))

                    if ioc.get('component') is not None:
                        raise Exception('Cannot override iocs from components')

                    self._add_ioc(ioc['name'], autostart=ioc.get('autostart'), restart=ioc.get('restart'),
                                  macros=macros, pvs=pvs, pvsets=pvsets, simlevel=ioc.get('simlevel'))

            if "blocks" in details:
                # List of dicts
                for args in details["blocks"]:
                    if args.get('component') is not None:
                        raise Exception('Cannot override blocks from components')
                    self.add_block(args)
            if "groups" in details:
                # List of dicts
                for args in details["groups"]:
                    if args.get('component') is not None:
                        raise Exception('Cannot override groups from components')
                    self._set_group_details(details['groups'])
            if "name" in details:
                self._set_config_name(details["name"])
            if "description" in details:
                self._config.meta.description = details["description"]
            if "synoptic" in details:
                self._config.meta.synoptic = details["synoptic"]
            # blockserver ignores history returned by clients:
            if "history" in details:
                self._config.meta.history = details["history"]
            if "components" in details:
                # List of dicts
                for args in details["components"]:
                    comp = self.load_configuration(args['name'], True)
                    self.add_component(comp.get_name(), comp)
        except Exception as err:
            self._retrieve_cache()
            raise err

    def _to_dict(self, data_list):
        if data_list is None:
            return None
        out = dict()
        for item in data_list:
            out[item["name"]] = item
        return out

    def set_config(self, config, is_component=False):
        """ Replace the existing configuration with the supplied configuration.

        Args:
            config (Configuration): A configuration
            is_component (bool, optional): Whether it is a component
        """
        self.clear_config()
        self._config = config
        self._is_component = is_component
        self._components = OrderedDict()
        if not is_component:
            for n, v in config.components.iteritems():
                if n.lower() != DEFAULT_COMPONENT.lower():
                    comp = self.load_configuration(v.lower(), True)
                    self.add_component(v, comp)
            # add default component to list of components
            basecomp = self.load_configuration(DEFAULT_COMPONENT, True)
            self.add_component(DEFAULT_COMPONENT, basecomp)

    def _set_component_names(self, comp, name):
        # Set the component for blocks, groups and IOCs
        for n, v in comp.blocks.iteritems():
            v.component = name
        for n, v in comp.groups.iteritems():
            v.component = name
        for n, v in comp.iocs.iteritems():
            v.component = name

    def load_configuration(self, name, is_component=False, set_component_names=True):
        """ Load a configuration.

        Args:
            name (string): The name of the configuration to load
            is_component (bool, optional): Whether it is a component
            set_component_names (bool, optional): Whether to set the component names
        """
        if is_component:
            comp = self._filemanager.load_config(FILEPATH_MANAGER.get_component_path(name), name, self._macros)
            if set_component_names:
                self._set_component_names(comp, name)
            return comp
        else:
            return self._filemanager.load_config(FILEPATH_MANAGER.get_config_path(name), name, self._macros)

    def save_configuration(self, name, as_component):
        """ Save the configuration.

        Args:
            name (string): The name to save the configuration under
            as_component (bool): Whether to save as a component
        """
        self._check_name(name, as_component)
        if self._is_component != as_component:
            self._set_as_component(as_component)

        if self._is_component:
            self._set_config_name(name)
            self._filemanager.save_config(self._config, FILEPATH_MANAGER.get_component_path(name))
            self._update_version_control(name)
        else:
            self._set_config_name(name)
            # TODO: CHECK WHAT COMPONENTS self._config contains and remove _base if it is in there
            self._filemanager.save_config(self._config, FILEPATH_MANAGER.get_config_path(name))
            self._update_version_control(name)

    def _check_name(self, name, is_comp = False):
        # Not empty
        if name is None or name.strip() == "":
            raise Exception("Configuration name cannot be blank")
        #
        if is_comp and name.lower() == DEFAULT_COMPONENT.lower():
            raise Exception("Cannot save over default component")
        # Valid chars
        m = re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name)
        if m is None:
            raise Exception("Configuration name contains invalid characters")

    def _update_version_control(self, name):
        if self._is_component:
            self._vc.add(FILEPATH_MANAGER.get_component_path(name))
        else:
            self._vc.add(FILEPATH_MANAGER.get_config_path(name))

        self._vc.commit("%s modified by client" % name)

    def _set_as_component(self, value):
        if value is True:
            if len(self._components) == 0:
                self._is_component = True
            else:
                raise Exception("Can not cast to a component as the configuration contains at least one component")
        else:
            self._is_component = False

    def update_runcontrol_settings_for_saving(self, rc_data):
        """ Updates the run-control settings stored in the configuration so they can be saved.

        Args:
            rc_data (dict): The current run-control settings
        """
        self._config.update_runcontrol_settings_for_saving(rc_data)

    def _cache_config(self):
        self._cached_config = copy.deepcopy(self._config)
        self._cached_components = copy.deepcopy(self._components)

    def _retrieve_cache(self):
        self._config = copy.deepcopy(self._cached_config)
        self._components = copy.deepcopy(self._cached_components)

    def get_config_meta(self):
        """ Fetch the configuration's metadata.

        Returns:
            MetaData : The metadata for the configuration
        """
        return self._config.meta

    def get_cached_name(self):
        """ Get the previous name which may be the same as the current.

        Returns:
            string : The previous name
        """
        return self._cached_config.get_name()

    def set_history(self, history):
        """ Set history for configuration.

        Args:
            history (list): The new history
        """
        self._config.meta.history = history

    def get_history(self):
        """ Get the history for configuration.

        Returns:
            list : The history
        """
        return self._config.meta.history
