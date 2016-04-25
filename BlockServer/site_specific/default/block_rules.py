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

from server_common.utilities import compress_and_hex
import json

DISALLOWED_BLOCK_NAMES = ["lowlimit", "highlimit", "runcontrol", "wait"]
ALLOWED_BLOCK_NAME_REGEX = r"^[a-zA-Z]\w*$"
BLOCK_REGEX_ERROR_MESSAGE = "Block name must start with a letter and only contain letters, numbers and underscores"
BLOCK_RULES_PV = "BLOCK_RULES"


class BlockRules(object):
    """Class for managing exposing the rules for allowed block names"""

    def __init__(self, block_server):
        """Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance.
        """
        self._bs = block_server
        self.rules = {"disallowed": DISALLOWED_BLOCK_NAMES, "regex": ALLOWED_BLOCK_NAME_REGEX,
                      "regex_message": BLOCK_REGEX_ERROR_MESSAGE}
        self._create_pv()

    def _create_pv(self):
        self._bs.add_string_pv_to_db(BLOCK_RULES_PV, 16000)
        self._bs.setParam(BLOCK_RULES_PV, compress_and_hex(json.dumps(self.rules)))
        self._bs.updatePVs()

