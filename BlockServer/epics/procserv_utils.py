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
from server_common.channel_access import ChannelAccess
from server_common.utilities import print_and_log, ioc_restart_pending, retry


class ProcServWrapper(object):
    """A wrapper for accessing some of the functionality of ProcServ."""

    def __init__(self, prefix):
        """Constructor.
        Args:
            prefix (string): The prefix for the instrument
        """
        self.procserv_prefix = "{}CS:PS:".format(prefix)

    def start_ioc(self, ioc):
        """Starts the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log("Starting IOC %s" % ioc)
        ChannelAccess.caput(self.procserv_prefix + ioc + ":START", 1)

    def stop_ioc(self, ioc):
        """Stops the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log("Stopping IOC %s" % ioc)
        ChannelAccess.caput(self.procserv_prefix + ioc + ":STOP", 1)

    def restart_ioc(self, ioc):
        """Restarts the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log("Restarting IOC %s" % ioc)
        ChannelAccess.caput(self.procserv_prefix + ioc + ":RESTART", 1)

    def ioc_restart_pending(self, ioc):
        """Tests to see if an IOC restart is pending

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool: Whether a restart is pending
        """
        return ioc_restart_pending(self.procserv_prefix + ioc, ChannelAccess)

    def get_ioc_status(self, ioc):
        """Gets the status of the specified IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            string : The status
        """
        ans = ChannelAccess.caget(self.procserv_prefix + ioc + ":STATUS", as_string=True)
        if ans is None:
            raise Exception("Could not find IOC ({})".format(self.procserv_prefix + ioc))
        return ans.upper()

    def toggle_autorestart(self, ioc):
        """Toggles the auto-restart property.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC
        """
        # Check IOC is running, otherwise command is ignored
        print_and_log("Toggling auto-restart for IOC {}".format(ioc))
        ChannelAccess.caput(self.procserv_prefix + ioc + ":TOGGLE", 1)

    @retry(50, 0.1, ValueError)  # Retry for 5 seconds to get a valid value on failure
    def get_autorestart(self, ioc):
        """Gets the current auto-restart setting of the specified IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool : Whether auto-restart is enabled
        """
        ioc_prefix = self.procserv_prefix + ioc

        ans = ChannelAccess.caget("{}:AUTORESTART".format(ioc_prefix), as_string=True)
        if ans not in ["On", "Off"]:
            raise ValueError("Could not get auto-restart property for IOC {}, got '{}'".format(ioc_prefix, ans))

        return ans == "On"
