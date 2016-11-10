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

from BlockServer.mocks.mock_procserv_utils import MockProcServWrapper

IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')


class MockIocControl(object):

    def __init__(self, prefix):
        self._prefix = prefix
        self._proc = MockProcServWrapper()

    def start_ioc(self, ioc):
        self._proc.start_ioc(self._prefix, ioc)

    def restart_ioc(self, ioc, force, reapply_auto):
        self._proc.restart_ioc(self._prefix, ioc)

    def stop_ioc(self, ioc):
        self._proc.stop_ioc(self._prefix, ioc)

    def get_ioc_status(self, ioc):
        return self._proc.get_ioc_status(self._prefix, ioc)

    def start_iocs(self, iocs):
        for ioc in iocs:
            self._proc.start_ioc(self._prefix, ioc)

    def restart_iocs(self, iocs):
        for ioc in iocs:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self.restart_ioc(ioc)

    def stop_iocs(self, iocs):
        for ioc in iocs:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self._proc.stop_ioc(self._prefix, ioc)

    def ioc_exists(self, ioc):
        try:
            self.get_ioc_status(self._prefix, ioc)
            return True
        except:
            return False

