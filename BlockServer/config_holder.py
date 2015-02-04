import os
import copy
from config.file_manager import ConfigurationFileManager
from config.configuration import Configuration
from collections import OrderedDict
from config.constants import GRP_NONE
from config.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY, DEFAULT_COMPONENT
from config.containers import Group
from macros import PVPREFIX_MACRO


class ConfigHolder(object):
    def __init__(self, config_folder, macros, is_subconfig=False, file_manager=ConfigurationFileManager(),
                 test_config=None):
        if test_config is None:
            self._config = Configuration(macros)
            self._test_mode = False
        else:
            self._config = test_config
            self._test_mode = True
        self._components = OrderedDict()
        self._is_subconfig = is_subconfig
        self._macros = macros

        self._config_path = os.path.abspath(config_folder + CONFIG_DIRECTORY)
        self._component_path = os.path.abspath(config_folder + COMPONENT_DIRECTORY)
        self._filemanager = file_manager

        self._cached_config = Configuration(macros)
        self._cached_components = OrderedDict()

        if not os.path.isdir(self._config_path):
            # Create it
            os.makedirs(self._config_path)
        if not os.path.isdir(self._component_path):
            # Create it
            os.makedirs(self._component_path)

    def clear_config(self):
        self._config = Configuration(self._macros)
        self._components = OrderedDict()
        self._is_subconfig = False

    def is_subconfig(self):
        return self._is_subconfig

    def set_as_subconfig(self, value):
        if value is True:
            if len(self._components) == 0:
                self._is_subconfig = True
            else:
                raise Exception("Can not cast to a component as the configuration contains at least one component")
        else:
            self._is_subconfig = False

    def add_subconfig(self, name, component):
        # Add it to the holder
        if self._is_subconfig:
            raise Exception("Can not add a component to a component")

        if name.lower() not in self._components:
            # Add it
            component.set_name(name)
            self._components[name.lower()] = component
            self._config.subconfigs[name.lower()] = None  # Does not need to actual hold anything
        else:
            raise Exception("Requested component is already part of the current configuration: " + str(name))

    def remove_subconfig(self, name):
        # Remove it from the holder
        if self._is_subconfig:
            raise Exception("Can not remove a component from a component")
        del self._components[name.lower()]
        del self._config.subconfigs[name.lower()]

    def get_blocknames(self):
        # Get all the blocknames including those in the components
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
        blks = copy.deepcopy(self._config.blocks)
        for cn, cv in self._components.iteritems():
            for bn, bv in cv.blocks.iteritems():
                if bn not in blks:
                    blks[bn] = bv
        return blks

    def get_group_details(self):
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
                    # If group exists then append with subconfig group
                    # But don't add any duplicate blocks or blocks that don't exist
                    for bn in grp.blocks:
                        if bn not in groups[gn].blocks and bn not in used_blocks and bn in blocks:
                            groups[gn].blocks.append(bn)
                            used_blocks.append(bn)
        return groups

    def set_group_details(self, redefinition):
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
                # Not in config yet, so add it (it will override settings in any subconfigs)
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
        return self._config.get_name()

    def set_config_name(self, name):
        self._config.set_name(name)

    def get_ioc_names(self, includebase=False):
        iocs = self._config.iocs.keys()
        for cn, cv in self._components.iteritems():
            if includebase:
                iocs.extend(cv.iocs)
            elif cn.lower() != DEFAULT_COMPONENT.lower():
                iocs.extend(cv.iocs)
        return iocs

    def get_ioc_details(self):
        # TODO: make sure iocs are from default are returned
        iocs = copy.deepcopy(self._config.iocs)
        for cn, cv in self._components.iteritems():
            for n, v in cv.iocs.iteritems():
                if n not in iocs:
                    iocs[n] = v
        return iocs

    def get_component_names(self, includebase=False):
        l = list()
        for cn in self._components.keys():
            if includebase:
                l.append(cn)
            elif cn.lower() != DEFAULT_COMPONENT.lower():
                l.append(cn)
        return l

    def add_block(self, blockargs, subconfig=None):
        if subconfig is None:
            self._config.add_block(**blockargs)
        else:
            if subconfig.lower() in self._components:
                blockargs['subconfig'] = subconfig
                self._components[subconfig.lower()].add_block(**blockargs)
            else:
                raise Exception("No component called %s" % subconfig)

    def remove_block(self, name, subconfig=None):
        if subconfig is None:
            self._config.remove_block(name)
        else:
            if subconfig.lower() in self._components:
                self._components[subconfig.lower()].remove_block(name)
            else:
                raise Exception("No component called %s" % subconfig)

    def edit_block(self, blockargs, subconfig=None):
        if subconfig is None:
            self._config.edit_block(**blockargs)
        else:
            if subconfig.lower() in self._components:
                blockargs['subconfig'] = subconfig
                self._components[subconfig.lower()].edit_block(**blockargs)
            else:
                raise Exception("No component called %s" % subconfig)

    def add_ioc(self, name, subconfig=None, autostart=True, restart=True, macros=None, pvs=None, pvsets=None,
                simlevel=None):
        # TODO: use IOC object instead?
        if subconfig is None:
            self._config.add_ioc(name, None, autostart, restart, macros, pvs, pvsets, simlevel)
        else:
            if subconfig.lower() in self._components:
                self._components[subconfig.lower()].add_ioc(name, subconfig, autostart, restart, macros, pvs, pvsets,
                                                            simlevel)
            else:
                raise Exception("No component called %s" % subconfig)

    def remove_ioc(self, name, subconfig=None):
        if subconfig is None:
            self._config.remove_ioc(name)
        else:
            if subconfig.lower() in self._components:
                self._components[subconfig.lower()].remove_ioc(name)
            else:
                raise Exception("No component called %s" % subconfig)

    def get_config_details(self, include_subs=False):
        config = dict()
        if not include_subs:
            # Blocks, groups and IOC include the subconfig ones
            config['blocks'] = self._blocks_to_list(True)
            config['groups'] = self._groups_to_list()
            config['iocs'] = self._iocs_to_list()
            # Just return the names of the components
            config['components'] = self._comps_to_list()
            config['name'] = self._config.get_name()
            config['description'] = self._config.meta.description
        else:
            # TODO: This!
            pass
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

        for cn, cv in self._components.iteritems():
            for n, ioc in cv.iocs.iteritems():
                ioc_list.append(ioc.to_dict())
        return ioc_list

    def set_config_details_from_json(self, details):
        self._cache_config()

        try:
            self.clear_config()
            if "iocs" in details:
                # List of dicts
                for ioc in details["iocs"]:
                    macros = self._to_dict(ioc.get('macros'))
                    pvs = self._to_dict(ioc.get('pvs'))
                    pvsets = self._to_dict(ioc.get('pvsets'))

                    if ioc.get('subconfig') is not None:
                        raise Exception('Cannot override iocs from components')

                    self.add_ioc(ioc['name'], autostart=ioc.get('autostart'), restart=ioc.get('restart'),
                                 macros=macros, pvs=pvs, pvsets=pvsets, simlevel=ioc.get('simlevel'))

            if "blocks" in details:
                # List of dicts
                for args in details["blocks"]:
                    if args.get('subconfig') is not None:
                        raise Exception('Cannot override blocks from components')
                    self.add_block(args)
            if "groups" in details:
                # List of dicts
                for args in details["groups"]:
                    if args.get('subconfig') is not None:
                        raise Exception('Cannot override groups from components')
                    self.set_group_details(details['groups'])
            if "name" in details:
                self.set_config_name(details["name"])
            if "description" in details:
                self._config.meta.description = details["description"]
            if "components" in details:
                # List of dicts
                for args in details["components"]:
                    comp = self.load_config(args['name'], True)
                    self.add_subconfig(args['name'], comp)
        except:
            self._retrieve_cache()
            raise

    def _to_dict(self, json_list):
        if json_list is None:
            return None
        out = dict()
        for item in json_list:
            out[item.pop("name")] = item
        return out

    def set_config(self, config, is_subconfig=False):
        self.clear_config()
        self._config = config
        self._is_subconfig = is_subconfig
        self._components = OrderedDict()
        if not is_subconfig:
            # TODO: LOAD default/BASE component/subconfig HERE
            for n, v in config.subconfigs.iteritems():
                comp = self.load_config(n, True)
                self.add_subconfig(n, comp)
            # add default subconfig to list of subconfigs
            basecomp = self.load_config(DEFAULT_COMPONENT, True)
            self.add_subconfig(DEFAULT_COMPONENT, basecomp)

    def _set_component_names(self, comp, name):
            # Set the subconfig for blocks, groups and IOCs
            for n, v in comp.blocks.iteritems():
                v.subconfig = name
            for n, v in comp.groups.iteritems():
                v.subconfig = name
            for n, v in comp.iocs.iteritems():
                v.subconfig = name

    def load_config(self, name, is_subconfig=False, set_subconfig_names=True):
        if is_subconfig:
            path = self._component_path
            comp = self._filemanager.load_config(path, name, self._macros)
            if set_subconfig_names:
                self._set_component_names(comp, name)
            return comp
        else:
            path = self._config_path
            return self._filemanager.load_config(path, name, self._macros)

    def save_config(self, name):
        if self._is_subconfig:
            if name.lower() == DEFAULT_COMPONENT.lower():
                raise Exception("Cannot save over default component")
            self.set_config_name(name)
            self._filemanager.save_config(self._config, self._component_path, name, self._test_mode)
        else:
            self.set_config_name(name)
            # TODO: CHECK WHAT COMPONENTS self._config contains and remove _base if it is in there
            self._filemanager.save_config(self._config, self._config_path, name, self._test_mode)

    def update_runcontrol_settings_for_saving(self, rc_data):
        self._config.update_runcontrol_settings_for_saving(rc_data)

    def _cache_config(self):
        self._cached_config = copy.deepcopy(self._config)
        self._cached_components = copy.deepcopy(self._components)

    def _retrieve_cache(self):
        self._config = copy.deepcopy(self._cached_config)
        self._components = copy.deepcopy(self._cached_components)

    def get_config_meta(self):
        return self._config.meta

    def set_testing_mode(self, mode):
        self._test_mode = mode