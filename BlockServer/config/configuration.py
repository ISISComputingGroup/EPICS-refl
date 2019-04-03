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

""" Contains all the code for defining a configuration or component"""
from collections import OrderedDict

from BlockServer.config.group import Group
from BlockServer.config.block import Block
from BlockServer.config.ioc import IOC
from BlockServer.config.metadata import MetaData
from BlockServer.core.constants import GRP_NONE
from BlockServer.core.macros import PVPREFIX_MACRO
from server_common.utilities import print_and_log


class Configuration(object):
    """ The Configuration class.

    Attributes:
        blocks (OrderedDict): The blocks for the configuration
        macros (dict): The EPICS/BlockServer related macros
        groups (OrderedDict): The groups for the configuration
        iocs (OrderedDict): The IOCs for the configuration
        meta (MetaData): The meta-data for the configuration
        components (OrderedDict): The components which are part of the configuration
        is_component (bool): Whether it is actually a component
    """
    def __init__(self, macros):
        """ Constructor.

        Args:
            macros (dict): The dictionary containing the macros
        """
        # All dictionary keys are lowercase except iocs which is uppercase
        self.blocks = OrderedDict()
        self.macros = macros
        self.groups = OrderedDict()
        self.iocs = OrderedDict()
        self.meta = MetaData("")
        self.components = OrderedDict()
        self.is_component = False

    def add_block(self, name, pv, group=GRP_NONE, local=True, **kwargs):
        """ Add a block to the configuration.

        Args:
            name (string): The name for the new block
            pv (string): The PV that is aliased
            group (string, optional): The group that the block belongs to
            local (bool, optional): Is the block local
            kwargs (dict): Keyword arguments for the other parameters
        """
        # Check block name is unique
        if name.lower() in self.blocks.keys():
            raise ValueError("Failed to add block as name is not unique")

        if local:
            # Strip off the MYPVPREFIX in the PV name (not the block name!)
            pv = pv.replace(self.macros[PVPREFIX_MACRO], "")

        self.blocks[name.lower()] = Block(name, pv, local, **kwargs)

        if group is not None:
            # If group does not exists then add it
            if group.lower() not in self.groups.keys():
                self.groups[group.lower()] = Group(group)
            self.groups[group.lower()].blocks.append(name)

    def add_ioc(self, name, component=None, autostart=None, restart=None, macros=None, pvs=None, pvsets=None,
                simlevel=None):
        """ Add an IOC to the configuration.

        Args:
            name (string): The name of the IOC to add
            component (string, optional): The component that the IOC belongs to
            autostart (bool, optional): Should the IOC automatically start
            restart (bool, optional): Should the IOC automatically restart
            macros (dict, optional): The macro sets relating to the IOC
            pvs (, optional):
            pvsets (, optional): Any PV values that should be set at start up
            simlevel (, optional): Sets the simulation level

        """
        # Only add it if it has not been added before
        if name.upper() in self.iocs.keys():
            print_and_log("Warning: IOC '{}' is already part of the configuration. Not adding it again.")
        else:
            self.iocs[name.upper()] = IOC(name, autostart, restart, component, macros, pvs, pvsets, simlevel)

    def update_runcontrol_settings_for_saving(self, rc_data):
        """ Updates the run-control settings for the configuration's blocks.

        Args:
            rc_data (dict): A dictionary containing all the run-control settings
        """
        # Only do it for blocks that are not in a component
        for bn, blk in self.blocks.iteritems():
            if blk.component is None and blk.name in rc_data.keys():
                blk.rc_enabled = rc_data[blk.name]['ENABLE']
                blk.rc_lowlimit = rc_data[blk.name]['LOW']
                blk.rc_highlimit = rc_data[blk.name]['HIGH']

    def get_name(self):
        """ Gets the name of the configuration.

        Returns:
            string : The name of this configuration
        """
        return self.meta.name

    def set_name(self, name):
        """ Sets the configuration's name.

        Args:
            name (string): The new name for the configuration
        """
        self.meta.name = name
