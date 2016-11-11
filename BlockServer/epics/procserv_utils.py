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
from server_common.utilities import print_and_log, ioc_restart_pending


class ProcServWrapper(object):
    """A wrapper for accessing some of the functionality of ProcServ."""

    @staticmethod
    def generate_prefix(prefix, ioc):
        """Generate the PV prefix for an IOCs ProcServ.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC

        Returns:
            string : The PV prefix
        """
        return "%sCS:PS:%s" % (prefix, ioc)

    def start_ioc(self, prefix, ioc):
        """Starts the specified IOC.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC
        """
        print_and_log("Starting IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":START", 1)

    def stop_ioc(self, prefix, ioc):
        """Stops the specified IOC.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC
        """
        print_and_log("Stopping IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":STOP", 1)

    def restart_ioc(self, prefix, ioc):
        """Restarts the specified IOC.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC
        """
        print_and_log("Restarting IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":RESTART", 1)

    def ioc_restart_pending(self, prefix, ioc):
        """Tests to see if an IOC restart is pending

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC

        Returns:
            bool: Whether a restart is pending
        """
        return ioc_restart_pending(self.generate_prefix(prefix, ioc),ChannelAccess)

    def get_ioc_status(self, prefix, ioc):
        """Gets the status of the specified IOC.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC

        Returns:
            string : The status
        """
        ans = ChannelAccess.caget(self.generate_prefix(prefix, ioc) + ":STATUS", as_string=True)
        if ans is None:
            raise Exception("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        return ans.upper()

    def toggle_autorestart(self, prefix, ioc):
        """Toggles the auto-restart property.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC
        """
        # Check IOC is running, otherwise command is ignored
        print_and_log("Toggling auto-restart for IOC %s" % ioc)
        ChannelAccess.caput(self.generate_prefix(prefix, ioc) + ":TOGGLE", 1)

    def get_autorestart(self, prefix, ioc):
        """Gets the current auto-restart setting of the specified IOC.

        Args:
            prefix (string): The prefix for the instrument
            ioc (string): The name of the IOC

        Returns:
            bool : Whether auto-restart is enabled
        """
        ans = ChannelAccess.caget(self.generate_prefix(prefix, ioc) + ":AUTORESTART", as_string=True)
        if ans is None:
            raise Exception("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        elif ans == "On":
            return True
        elif ans == "Off":
            return False
        else:
            raise Exception("Could not get auto-restart property for IOC (%s)" % self.generate_prefix(prefix, ioc))
