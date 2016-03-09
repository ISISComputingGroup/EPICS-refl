'''
This file is part of the ISIS IBEX application.
Copyright (C) 2012-2015 Science & Technology Facilities Council.
All rights reserved.

This program is distributed in the hope that it will be useful.
This program and the accompanying materials are made available under the
terms of the Eclipse Public License v1.0 which accompanies this distribution.
EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.

You should have received a copy of the Eclipse Public License v1.0
along with this program; if not, you can obtain a copy from
https://www.eclipse.org/org/documents/epl-v10.php or 
http://opensource.org/licenses/eclipse-1.0.php
'''

class MockProcServWrapper(object):

    def __init__(self):
        self.ps_status = dict()
        self.ps_status["simple1"] = "SHUTDOWN"
        self.ps_status["simple2"] = "SHUTDOWN"
        self.ps_status["testioc"] = "SHUTDOWN"
        self.ps_status["stopdioc"] = "SHUTDOWN"

    @staticmethod
    def generate_prefix(prefix, ioc):
        return "%sCS:PS:%s" % (prefix, ioc)

    def start_ioc(self, prefix, ioc):
        self.ps_status[ioc.lower()] = "RUNNING"

    def stop_ioc(self, prefix, ioc):
        """Stops the specified IOC"""
        self.ps_status[ioc.lower()] = "SHUTDOWN"

    def restart_ioc(self, prefix, ioc):
        self.ps_status[ioc.lower()] = "RUNNING"

    def get_ioc_status(self, prefix, ioc):
        if not ioc.lower() in self.ps_status.keys():
            raise Exception("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        else:
            return self.ps_status[ioc.lower()]

    def ioc_exists(self, prefix, ioc):
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except:
            return False
