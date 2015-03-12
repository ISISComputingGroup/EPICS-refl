"""Contains all the code for defining a configuration or component"""
from collections import OrderedDict

from BlockServer.config.containers import Group, Block, IOC, MetaData
from BlockServer.core.constants import GRP_NONE
from BlockServer.core.macros import PVPREFIX_MACRO


class Configuration(object):
    """The configuration class.

    Attributes:
        blocks (OrderedDict) : The blocks for the configuration
        macros (dict) : The EPICS/BlockServer related macros
        groups (OrderedDict) : The groups for the configuration
        iocs (OrderedDict) : The IOCs for the configuration
        meta (MetaData) : The meta-data for the configuration
        subconfigs (OrderedDict) : The components which are part of the configuration
        is_component (bool) : Whether it is actually a component
    """
    def __init__(self, macros):
        """Constructor.

        Args:
            macros (dict) : The dictionary containing the macros
        """
        # All dictionary keys are lowercase except iocs which is uppercase
        self.blocks = OrderedDict()
        self.macros = macros
        self.groups = OrderedDict()
        self.iocs = OrderedDict()
        self.meta = MetaData("")
        self.subconfigs = OrderedDict()
        self.is_component = False

    def add_block(self, name, pv, group=GRP_NONE, local=True, **kwargs):
        """Add a block to the configuration.

        Args:
            name (string) : The name for the new block
            pv (string) : The PV that is aliased
            group (string) : The group that the block belongs to [optional]
            local (bool) : Is the block local [optional]
            kwargs (dict) : Keyword arguments for the other parameters
        """
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

    def add_ioc(self, name, subconfig=None, autostart=None, restart=None, macros=None, pvs=None, pvsets=None,
                simlevel=None):
        """Add an IOC to the configuration.

        Args:
            name (string) : The name of the IOC to add
            subconfig (string) : The component that the IOC belongs to [optional]
            autorestart (bool) : Should the IOC auto-restart [optional]
            restart (bool) :
            macros (dict) : The macro sets relating to the IOC [optional]
            pvs () :
            pvsets () : Any PV values that should be set at start up [optional]
            simlevel () : Sets the simulation level [optional]

        """
        # Only add it if it has not been added before
        if not name.upper() in self.iocs.keys():
            self.iocs[name.upper()] = IOC(name, autostart, restart, subconfig, macros, pvs, pvsets, simlevel)

    def update_runcontrol_settings_for_saving(self, rc_data):
        """Updates the run-control settings for the configuration's blocks.

        Args:
            rc_data (dict) : A dictionary containing all the run-control settings
        """
        # Only do it for blocks that are not in a sub-config
        for bn, blk in self.blocks.iteritems():
            if blk.subconfig is None and blk.save_rc_settings:
                if blk.name in rc_data.keys():
                    blk.rc_enabled = rc_data[blk.name]['ENABLE']
                    blk.rc_lowlimit = rc_data[blk.name]['LOW']
                    blk.rc_highlimit = rc_data[blk.name]['HIGH']

    def get_name(self):
        """Gets the name of the configuration.

        Returns:
            string : The name of this configuration
        """
        return self.meta.name

    def set_name(self, name):
        """Sets the configuration's name.

        Args:
            name (string) : The new name for the configuration
        """
        self.meta.name = name


