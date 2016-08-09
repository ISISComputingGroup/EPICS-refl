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


class IocOptions(object):
    """Contains the possible macros and pvsets of an IOC"""
    def __init__(self, name, macros=None, pvsets=None, pvs=None):
        """Constructor

        Args:
            name (string): The name of the IOC the options are associated with
            macros (dict, optional): A dict of the possible macros for the IOC, along with a list of associated
                                      parameters (description, pattern etc.)
            pvsets (dict, optional): A dict of the possible pvsets for the IOC, along with a list of associated
                                      parameters (description etc.)
            pvs (dict, optional): A dict of the possible pvs for the IOC, along with a list of associated parameters
                                   (description etc.)
        """
        if macros is None:
            self.macros = dict()
        else:
            self.macros = macros

        if pvsets is None:
            self.pvsets = dict()
        else:
            self.pvsets = pvsets

        if pvs is None:
            self.pvs = dict()
        else:
            self.pvs = pvs

        self.name = name

    def _dict_to_list(self, in_dict):
        # Convert into format for better GUI parsing (I know it's messy but it's what the GUI wants)
        out_list = []
        for k, v in in_dict.iteritems():
            v['name'] = k
            out_list.append(v)
        return out_list

    def to_dict(self):
        """Get a dictionary of the possible macros and pvsets for an IOC

        Returns:
            dict : Possible macros and pvsets
        """
        return {'macros': self._dict_to_list(self.macros), 'pvsets': self._dict_to_list(self.pvsets),
                'pvs': self._dict_to_list(self.pvs)}
