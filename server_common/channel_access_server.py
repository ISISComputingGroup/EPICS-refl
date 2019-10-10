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

from builtins import str
from pcaspy import SimpleServer, Driver, cas
import re


class DynamicStringPV(cas.casPV):
    """A class that inherits from casPV to create a PV type for holding char arrays as strings."""

    def __init__(self, data):
        """Constructor

        Args:
            data (string): The initial data held in the PV
        """
        super(DynamicStringPV, self).__init__()
        self.stored_value = cas.gdd()
        self.stored_value.setPrimType(cas.aitEnumUint8)
        self.stored_value.put(data)

    def getValue(self, value):
        """Overrides the getValue method in cas.casPV. Used by pcaspy to get the value of the PV.

        Args:
            value (gdd): A gdd object used to store the PV's value.

        Returns:
            cas.S_casApp_success if successful
        """
        if value.primitiveType() == cas.aitEnumInvalid:
            value.setPrimType(cas.aitEnumUint8)
        value.put(self.stored_value.get())
        return cas.S_casApp_success

    def updateValue(self, value):
        """Overrides the updateValue method in cas.casPV. Used by pcaspy to update the value of the PV.

        Args:
            value (gdd): A gdd object which holds the new value for the PV.
        """
        self.stored_value.put(value)
        self.stored_value.setTimeStamp()
        self.postEvent(self.stored_value)

    def maxDimension(self):
        """Overrides the maxDimension method in cas.casPV. Used by pcaspy to find the dimensions of the PV data."""
        return 1

    def maxBound(self, dims):
        """Overrides the maxBound method in cas.casPV. Used by pcaspy to find the bounds of the PV data."""
        return 16000

    def bestExternalType(self):
        """Overrides the bestExternalType method in cas.casPV. Used by pcaspy to find the type of the PV data."""
        return cas.aitEnumUint8


class CAServer(SimpleServer):
    """A class that inherits from SimpleServer to create our own Channel Access server. This allows us to dynamically
    add/remove PVs at runtime
    """

    def __init__(self, pv_prefix):
        """Initialisation requires a prefix that all PVs associated with this server will contain.
        """
        super(CAServer, self).__init__()
        self._pvs = dict()
        self._prefix = pv_prefix

    def _strip_prefix(self, fullname):
        pvmatch = re.match(self._prefix + r'(.*)', fullname)
        if pvmatch is not None:
            return pvmatch.group(1)
        else:
            return None

    def pvExistTest(self, context, addr, fullname):
        """A method that overrides the SimpleServer pvExistTest method. It is called by channel access to check if a PV
        exists at this server. The method first checks against the dictionary at this server and then checks against the
        parent SimpleServer.
        """
        try:
            pv = self._strip_prefix(fullname)
            if pv is not None and pv in self._pvs:
                return cas.pverExistsHere
            else:
                return SimpleServer.pvExistTest(self, context, addr, fullname)
        except:
            return cas.pverDoesNotExistHere

    def pvAttach(self, context, fullname):
        """A method that overrides the SimpleServer pvAttach method. It is called by channel access to attach a monitor
        to the specified PV. The method first checks against the dictionary at this server and then checks against the
        parent SimpleServer.
        """
        pv = self._strip_prefix(fullname)
        if pv is not None and pv in self._pvs:
            return self._pvs[pv]
        else:
            return SimpleServer.pvAttach(self, context, fullname)

    def registerPV(self, name, data=''):
        """Creates a PV in the dictionary of this server.

        Args:
            name (string): The name of the PV to create (without the PV prefix)
            data (string, optional): The initial data stored in the PV
        """
        if name not in self._pvs:
            self._pvs[name] = DynamicStringPV(data)

    def updatePV(self, name, data):
        """Updates a PV in the dictionary of this server. The PV will be created if it does not exist.

        Args:
            name (string): The name of the PV to update (without the PV prefix)
            data (string): The data to store in the PV
        """
        if name in self._pvs:
            self._pvs[name].updateValue(data)
        else:
            self.registerPV(name, data)

    def deletePV(self, name):
        """Removes a PV from the dictionary of this server.

        Args:
            name (string): The name of the PV to remove (without the PV prefix)
        """
        if name in self._pvs:
            del self._pvs[name]

if __name__ == '__main__':
    # Here for testing
    prefix = 'MTEST:'
    pvdb = { 'STATIC': {} }

    server = CAServer(prefix)
    server.createPV(prefix, pvdb)
    driver = Driver()

    server.registerPV("TEST")
    server.updatePV("TEST", "TEST initialised, this is a really long string designed to test whether the end is cut off if it is over 40 characters")

    i = 0

    while True:
        try:
            server.process(0.1)
            i += 1
            if (i % 100) == 0:
                server.updatePV("TEST", "I is: " + str(i))
        except KeyboardInterrupt:
            break
