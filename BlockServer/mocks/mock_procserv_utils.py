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


class MockProcServWrapper(object):

    def __init__(self, prefix):
        self.ps_status = dict()
        self.ps_status["simple1"] = "SHUTDOWN"
        self.ps_status["simple2"] = "SHUTDOWN"
        self.ps_status["testioc"] = "SHUTDOWN"
        self.autorestart = False
        self.restarting = False
        self.prefix = prefix + "CS:PS:"

    def start_ioc(self, ioc):
        self.ps_status[ioc.lower()] = "RUNNING"

    def stop_ioc(self, ioc):
        """Stops the specified IOC"""
        self.ps_status[ioc.lower()] = "SHUTDOWN"

    def ioc_restart_pending(self, ioc):
        """Return the currently restarting state then complete the pending restart"""
        restarting = self.restarting
        self.restarting = False
        return restarting

    def restart_ioc(self, ioc):
        self.restarting = True
        self.ps_status[ioc.lower()] = "RUNNING"

    def get_ioc_status(self, ioc):
        if not ioc.lower() in self.ps_status.keys():
            raise Exception("Could not find IOC ({})".format(self.prefix + ioc))
        else:
            return self.ps_status[ioc.lower()]

    def ioc_exists(self, ioc):
        try:
            self.get_ioc_status(ioc)
            return True
        except:
            return False

    def get_autorestart(self, ioc):
        return self.autorestart

    def toggle_autorestart(self, ioc):
        self.autorestart = not self.autorestart
