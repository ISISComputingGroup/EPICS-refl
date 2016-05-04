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
from BlockServer.site_specific.default.general_rules import REGEX_PV_NAME_LIKE, REGEX_ERROR_TEMPLATE_PV_NAME
from server_common.utilities import compress_and_hex
import json

DISALLOWED_BLOCK_NAMES = ["lowlimit", "highlimit", "runcontrol", "wait"]
BLOCK_REGEX_ERROR_MESSAGE = REGEX_ERROR_TEMPLATE_PV_NAME.format("Block name")
BLOCK_RULES_PV = "BLOCK_RULES"


class BlockRules(object):
    """Class for managing exposing the rules for allowed block names"""

    def __init__(self, cas):
        """Constructor.

        Args:
            cas (CAServer): The channel access server for creating PVs on-the-fly
        """
        self._cas = cas
        self._create_pv()

    def _create_pv(self):
        data = {"disallowed": DISALLOWED_BLOCK_NAMES,
                "regex": REGEX_PV_NAME_LIKE,
                "regexMessage": BLOCK_REGEX_ERROR_MESSAGE}
        self._cas.updatePV(BLOCK_RULES_PV, compress_and_hex(json.dumps(data)))
