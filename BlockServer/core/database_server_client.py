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

from server_common.utilities import dehex_and_decompress
import json
from server_common.channel_access import caget


class DatabaseServerClient(object):
    """Class for talking to the DatabaseServer.
    """
    def __init__(self, blockserver_prefix):
        """ Constructor.

        Args:
            blockserver_prefix (string): The prefix for the BlockServer
        """
        self._blockserver_prefix = blockserver_prefix

    def get_iocs(self):
        """ Get a list of IOCs from DatabaseServer.

        Returns:
            list : A list of IOC names
        """
        rawjson = dehex_and_decompress(caget(self._blockserver_prefix + "IOCS"))
        return json.loads(rawjson).keys()
