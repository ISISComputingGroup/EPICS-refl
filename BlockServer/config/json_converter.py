#This file is part of the ISIS IBEX application.
#Copyright (C) 2012-2016 Science & Technology Facilities Council.
#All rights reserved.
#
#This program is distributed in the hope that it will be useful.
#This program and the accompanying materials are made available under the
#terms of the Eclipse Public License v1.0 which accompanies this distribution.
#EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
#AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
#OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
#You should have received a copy of the Eclipse Public License v1.0
#along with this program; if not, you can obtain a copy from
#https://www.eclipse.org/org/documents/epl-v10.php or 
#http://opensource.org/licenses/eclipse-1.0.php

import json
from collections import OrderedDict

from BlockServer.core.constants import GRP_NONE


class ConfigurationJsonConverter(object):
    """Helper class for converting configuration data to and from JSON.

    Consists of static methods only.

    """

    @staticmethod
    def _groups_to_list(groups):
        grps = list()
        if groups is not None:
            for group in groups.values():
                if group.name.lower() != GRP_NONE.lower():
                    grps.append({"name": group.name, "component": group.component, "blocks": group.blocks})

            # Add NONE group at end
            if GRP_NONE.lower() in groups.keys():
                grps.append({"name": GRP_NONE, "component": None, "blocks": groups[GRP_NONE.lower()].blocks})
        return grps

    @staticmethod
    def groups_to_json(groups):
        """ Converts the groups dictionary to a JSON list

        Args:
            groups (OrderedDict): The groups to convert to JSON

        Returns:
            string : The groups as a JSON list
        """
        grps = ConfigurationJsonConverter._groups_to_list(groups)
        return json.dumps(grps)
