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

from server_common.channel_access import ChannelAccess
from server_common.utilities import print_and_log


class ProcServWrapper(object):
    """A wrapper for ProcSev to allow for control of IOCs"""

    def __init__(self):
        pass

    @staticmethod
    def generate_prefix(prefix, ioc):
        """Creates a PV based on the given prefix and IOC name

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the requested IOC
        """
        return "%sCS:PS:%s" % (prefix, ioc)

    def start_ioc(self, prefix, ioc):
        """Starts the specified IOC

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the IOC to start
        """
        print_and_log("Starting IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":START", 1)

    def stop_ioc(self, prefix, ioc):
        """Stops the specified IOC

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the IOC to stop
        """
        print_and_log("Stopping IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":STOP", 1)

    def restart_ioc(self, prefix, ioc):
        """Restarts the specified IOC

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the IOC to restart
        """
        print_and_log("Restarting IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":RESTART", 1)

    def get_ioc_status(self, prefix, ioc):
        """Gets the status of the specified IOC

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the IOC

        Returns:
            string : The status of the requested IOC
        """
        pv = self.generate_prefix(prefix, ioc) + ":STATUS"
        ans = ChannelAccess.caget(pv, as_string=True)
        if ans is None:
            raise Exception("Could not find IOC (%s)" % pv)
        return ans.upper()

    def ioc_exists(self, prefix, ioc):
        """Checks if the IOC exists on ProcServ

        Args:
            prefix (string): The prefix of the instrument the IOC is being run on
            ioc (string): The name of the IOC

        Returns:
            bool : True if IOC exists, False otherwise
        """
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except:
            return False