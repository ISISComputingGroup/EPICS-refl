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

from time import sleep, time

from BlockServer.epics.procserv_utils import ProcServWrapper
from BlockServer.alarm.load_alarm_config import AlarmConfigLoader
from server_common.utilities import print_and_log

IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL', 'ALARM')


class IocControl(object):
    """A class for starting, stopping and restarting IOCs"""
    def __init__(self, prefix, proc=ProcServWrapper()):
        """Constructor.

        Args:
            prefix (string): The PV prefix for the instrument
            proc (ProcServWrapper, optional): The underlying object for talking to ProcServ
        """
        self._prefix = prefix
        self._proc = proc

    def start_ioc(self, ioc):
        """Start an IOC.

        Args:
            ioc (string): The name of the IOC
        """
        try:
            self._proc.start_ioc(self._prefix, ioc)
            if ioc != "ALARM":
                AlarmConfigLoader.restart_alarm_server(self)
        except Exception as err:
            print_and_log("Could not start IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def restart_ioc(self, ioc, force=False):
        """Restart an IOC.

        Note: restarting an IOC automatically sets the IOC to auto-restart, so it is neccessary to reapply the
        previous auto-restart setting

        Args:
            ioc (string): The name of the IOC
            force (bool): Force it to restart even if it is an IOC not to stop
        """
        # Check it is okay to stop it
        if not force and ioc.startswith(IOCS_NOT_TO_STOP):
            return
        try:
            auto = self._proc.get_autorestart(self._prefix, ioc)
            self._proc.restart_ioc(self._prefix, ioc)
            if ioc != "ALARM":
                AlarmConfigLoader.restart_alarm_server(self)
        except Exception as err:
            print_and_log("Could not restart IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def stop_ioc(self, ioc, force=False):
        """Stop an IOC.

        Args:
            ioc (string): The name of the IOC
            force (bool): Force it to stop even if it is an IOC not to stop
        """
        # Check it is okay to stop it
        if not force and ioc.startswith(IOCS_NOT_TO_STOP):
            return
        try:
            self._proc.stop_ioc(self._prefix, ioc)
            if ioc != "ALARM":
                AlarmConfigLoader.restart_alarm_server(self)
        except Exception as err:
            print_and_log("Could not stop IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def get_ioc_status(self, ioc):
        """Get the running status of an IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            string : The status of the IOC (RUNNING or SHUTDOWN)
        """
        return self._proc.get_ioc_status(self._prefix, ioc)

    def ioc_restart_pending(self, ioc):
        """Tests if the IOC has a pending restart

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool : Whether a restart is pending
        """
        return self._proc.ioc_restart_pending(self._prefix, ioc)

    def start_iocs(self, iocs):
        """ Start a number of IOCs.

        Args:
            iocs (list): The IOCs to start
        """
        for ioc in iocs:
            self.start_ioc(ioc)

    def restart_iocs(self, iocs, reapply_auto=False):
        """ Restart a number of IOCs.

        Args:
            iocs (list): The IOCs to restart
            reapply_auto (bool): Whether to reapply auto restart settings automatically
        """
        auto = dict()
        for ioc in iocs:
            auto[ioc] = self.get_autorestart(ioc)
            self.restart_ioc(ioc)

        # Reapply auto-restart settings
        if reapply_auto:
            for ioc in iocs:
                self.waitfor_running(ioc)
                self.set_autorestart(ioc, auto[ioc])

    def stop_iocs(self, iocs):
        """ Stop a number of IOCs.

        Args:
            iocs (list): The IOCs to stop
        """
        for ioc in iocs:
            self.stop_ioc(ioc)

    def ioc_exists(self, ioc):
        """Checks an IOC exists.

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool : Whether the IOC exists
        """
        try:
            self.get_ioc_status(ioc)
            return True
        except:
            return False

    def set_autorestart(self, ioc, enable):
        """Used to set the auto-restart property.

        Args:
            ioc (string): The name of the IOC
            enable (bool): Whether to enable auto-restart
        """
        try:
            if self.get_ioc_status(ioc) == "RUNNING":
                # Get current auto-restart status
                curr = self._proc.get_autorestart(self._prefix, ioc)
                if curr != enable:
                    # If different to requested then change it
                    self._proc.toggle_autorestart(self._prefix, ioc)
                    return
                print_and_log("Auto-restart for IOC %s unchanged as value has not changed" % ioc)
            else:
                print_and_log("Auto-restart for IOC %s unchanged as IOC is not running" % ioc)
        except Exception as err:
            print_and_log("Could not set auto-restart IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def get_autorestart(self, ioc):
        """Gets the current auto-restart setting of the specified IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool : Whether auto-restart is enabled
        """
        try:
            return self._proc.get_autorestart(self._prefix, ioc)
        except Exception as err:
            print_and_log("Could not get auto-restart setting for IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def waitfor_running(self, ioc, timeout=5):
        """Waits for the IOC to start running.

        Args:
            ioc (string): The name of the IOC
            timeout(int, optional): Maximum time to wait before returning
        """
        if self.ioc_exists(ioc):
            start = time()
            while self.ioc_restart_pending(ioc) or self.get_ioc_status(ioc) != "RUNNING":
                sleep(0.5)
                if time() - start >= timeout:
                    print_and_log("Gave up waiting for IOC %s to be running" % ioc, "MAJOR")
                    return
