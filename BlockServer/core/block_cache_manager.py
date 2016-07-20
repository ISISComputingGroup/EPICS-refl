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

from server_common.utilities import print_and_log

BLOCKCACHE_PSC = "BLOCKCACHE"


class BlockCacheManager(object):
    """The BlockCache is a separate Python CAS which holds the current block values for use in cshow.
    This class allows the Block Server to control that CAS via ProcServCtrl.
    """
    def __init__(self, ioc_control):
        """Constructor.

        Args:
            ioc_control (IocControl): The object for restarting the IOC
        """
        self._ioc_control = ioc_control

    def restart(self):
        """ Restarts via ProcServCtrl.
        """
        try:
            if self._ioc_control.get_ioc_status(BLOCKCACHE_PSC) == "RUNNING":
                self._ioc_control.restart_ioc(BLOCKCACHE_PSC, force=True)
            else:
                self._ioc_control.start_ioc(BLOCKCACHE_PSC)
        except Exception as err:
            print_and_log("Problem with restarting the Block Cache: %s" % str(err), "MAJOR")