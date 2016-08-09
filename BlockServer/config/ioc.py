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

import copy


class IOC(object):
    """ Represents an IOC.

    Attributes:
        name (string): The name of the IOC
        autostart (bool): Whether the IOC should automatically start
        restart (bool): Whether the IOC should automatically restart
        component (string): The component the IOC belongs to
        macros (dict): The IOC's macros
        pvs (dict): The IOC's PVs
        pvsets (dict): The IOC's PV sets
        simlevel (string): The level of simulation
    """
    def __init__(self, name, autostart=True, restart=True, component=None, macros=None, pvs=None, pvsets=None,
                 simlevel=None):
        """ Constructor.

        Args:
            name (string): The name of the IOC
            autostart (bool): Whether the IOC should automatically start
            restart (bool): Whether the IOC should automatically restart
            component (string): The component the IOC belongs to
            macros (dict): The IOC's macros
            pvs (dict): The IOC's PVs
            pvsets (dict): The IOC's PV sets
            simlevel (string): The level of simulation
        """
        self.name = name
        self.autostart = autostart
        self.restart = restart
        self.component = component

        if simlevel is None:
            self.simlevel = "none"
        else:
            self.simlevel = simlevel.lower()

        if macros is None:
            self.macros = dict()
        else:
            self.macros = macros

        if pvs is None:
            self.pvs = dict()
        else:
            self.pvs = pvs

        if pvsets is None:
            self.pvsets = dict()
        else:
            self.pvsets = pvsets

    def _dict_to_list(self, in_dict):
        """ Converts into a format better for the GUI to parse, namely a list.

        It's messy but it's what the GUI wants.

        Args:
            in_dict (dict): The dictionary to be converted

        Returns:
            list : The newly created list
        """
        out_list = []
        for k, v in in_dict.iteritems():
            # Take a copy as we do not want to modify the original
            c = copy.deepcopy(v)
            c['name'] = k
            out_list.append(c)
        return out_list

    def __str__(self):
        data = "Name: %s, COMPONENT: %s" % (self.name, self.component)
        return data

    def to_dict(self):
        """ Puts the IOC's details into a dictionary.

        Returns:
            dict : The IOC's details
        """
        return {'name': self.name, 'autostart': self.autostart, 'restart': self.restart,
                'simlevel': self.simlevel, 'pvs': self._dict_to_list(self.pvs),
                'pvsets': self._dict_to_list(self.pvsets), 'macros': self._dict_to_list(self.macros),
                'component': self.component}