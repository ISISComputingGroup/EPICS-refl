"""Contains all the code for creating a configuration"""
from collections import OrderedDict

from BlockServer.config.containers import Group, Block, IOC, MetaData
from BlockServer.config.constants import GRP_NONE
from BlockServer.core.macros import PVPREFIX_MACRO


class Configuration(object):
    """The configuration"""
    def __init__(self, macros):
        """Constructor"""
        # All dictionary keys are lowercase except iocs which is uppercase
        self.blocks = OrderedDict()
        self.macros = macros
        self.groups = OrderedDict()
        self.iocs = OrderedDict()
        self.meta = MetaData("")
        self.subconfigs = OrderedDict()
        self.is_component = False

    def add_block(self, name, pv, group=GRP_NONE, local=True, **kwargs):
        """Add a block to the configuration"""
        # Check block name is unique
        if name.lower() in self.blocks.keys():
            raise Exception("Failed to add block as name is not unique")

        if local:
            # Strip off the MYPVPREFIX in the PV name (not the block name!)
            pv = pv.replace(self.macros[PVPREFIX_MACRO], "")
        self.blocks[name.lower()] = Block(name, pv, local, **kwargs)

        if group is not None:
            # If group does not exists then add it
            if not group.lower() in self.groups.keys():
                self.groups[group.lower()] = Group(group)
            self.groups[group.lower()].blocks.append(name)

    def remove_block(self, name):
        """Remove a block from the configuration"""
        # Does the block exist
        if name.lower() not in self.blocks.keys():
            raise Exception("Failed to remove block as it does not exist")

        # Remove from group first
        blk = self.blocks[name.lower()]
        for n, g in self.groups.iteritems():
            if blk.name in g.blocks:
                g.blocks.remove(blk.name)

        # Then remove from blocks
        del self.blocks[name.lower()]

    def edit_block(self, name, pv=None, local=None, new_name=None, **kwargs):
        """Edit an existing block"""
        # Does the block exist
        if name.lower() not in self.blocks.keys():
            raise Exception("Failed to edit block as it does not exist")

        blk = self.blocks[name.lower()]

        if pv is None:
            # Leave it as it was
            pv = blk.pv

        if local is None:
            # Leave it as it was
            local = blk.local

        if not "visible" in kwargs:
            # Leave it as it was
            kwargs["visible"] = blk.visible

        # Simplest solution is to delete the block and re-add it
        if new_name is not None and new_name.strip() != '' and new_name != name:
            # Does the new name exist
            if new_name.lower() in self.blocks.keys():
                raise Exception("Failed to rename block as the new name already exists")
            self.remove_block(name)
            # Replace with new name in any groups
            for n, g in self.groups.iteritems():
                for i in range(len(g.blocks)):
                    if g.blocks[i] == name:
                        g.blocks[i] = new_name
            name = new_name
        else:
            self.remove_block(name)
        # Send None for group name as we don't handle group changes here
        self.add_block(name, pv, None, local, **kwargs)

    def add_ioc(self, name, subconfig=None, autostart=None, restart=None, macros=None, pvs=None, pvsets=None, simlevel=None):
        # Only add it if it has not been added before
        if not name.upper() in self.iocs.keys():
            self.iocs[name.upper()] = IOC(name, autostart, restart, subconfig, macros, pvs, pvsets, simlevel)

    def update_runcontrol_settings_for_saving(self, rc_data):
        #TODO:
        # Only do it for blocks that are not in a sub-config
        for bn, blk in self.blocks.iteritems():
            if blk.subconfig is None and blk.save_rc_settings:
                if blk.name in rc_data.keys():
                    blk.rc_enabled = rc_data[blk.name]['ENABLE']
                    blk.rc_lowlimit = rc_data[blk.name]['LOW']
                    blk.rc_highlimit = rc_data[blk.name]['HIGH']

    def get_name(self):
        return self.meta.name

    def set_name(self, name):
        self.meta.name = name


