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

import json
import os
os.environ['MYDIRBLOCK'] = os.path.abspath('..')
os.environ['MYPVPREFIX'] = ""
os.environ['EPICS_KIT_ROOT'] = ""
os.environ['ICPCONFIGROOT'] = ""
import unittest

from DatabaseServer.database_server import DatabaseServer
from server_common.mocks.mock_ca_server import MockCAServer
from server_common.mocks.mock_ioc_data_source import MockIocDataSource, IOCS
from server_common.test_modules.test_ioc_data import HIGH_PV_NAMES, MEDIUM_PV_NAMES, FACILITY_PV_NAMES
from server_common.utilities import dehex_and_decompress
from DatabaseServer.mocks.mock_procserv_utils import MockProcServWrapper
from server_common.ioc_data import IOCData
from DatabaseServer.mocks.mock_exp_data import MockExpData
from server_common.constants import IS_LINUX
from server_common.pv_names import DatabasePVNames


class TestDatabaseServer(unittest.TestCase):
    def setUp(self):
        self.ms = MockCAServer()
        self.ioc_source = MockIocDataSource() # IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb"))
        self.proc_server = MockProcServWrapper()
        self.exp_data = MockExpData()
        self.ioc_data = IOCData(self.ioc_source, self.proc_server, "")
        test_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_files")
        self.db_server = DatabaseServer(self.ms, self.ioc_data, self.exp_data, test_files_dir, "block_prefix", True)

    @unittest.skipIf(IS_LINUX, "DB server not configured to run properly on Linux build")
    def test_interest_high_pvs_correct(self):
        pv_data = json.loads(dehex_and_decompress(self.db_server.read(DatabasePVNames.HIGH_INTEREST)))
        pv_names = []
        for item in pv_data:
            if len(item) > 0:
                pv_names.append(item[0])
        for name in HIGH_PV_NAMES:
            self.assertTrue(name in pv_names, msg="{name} in {pv_names}".format(name=name, pv_names=pv_names))

    @unittest.skipIf(IS_LINUX, "DB server not configured to run properly on Linux build")
    def test_interest_medium_pvs_correct(self):
        pv_data = json.loads(dehex_and_decompress(self.db_server.read(DatabasePVNames.MEDIUM_INTEREST)))
        pv_names = []
        for item in pv_data:
            if len(item) > 0:
                pv_names.append(item[0])
        for name in MEDIUM_PV_NAMES:
            self.assertTrue(name in pv_names, msg="{name} in {pv_names}".format(name=name, pv_names=pv_names))

    @unittest.skipIf(IS_LINUX, "DB server not configured to run properly on Linux build")
    def test_interest_facility_pvs_correct(self):
        pv_data = json.loads(dehex_and_decompress(self.db_server.read(DatabasePVNames.FACILITY)))
        pv_names = []
        for item in pv_data:
            if len(item) > 0:
                pv_names.append(item[0])
        for name in FACILITY_PV_NAMES:
            self.assertTrue(name in pv_names, msg="{name} in {pv_names}".format(name=name, pv_names=pv_names))

    @unittest.skipIf(IS_LINUX, "DB server not configured to run properly on Linux build")
    def test_iocs_pvs_correct(self):
        pv_data = json.loads(dehex_and_decompress(self.db_server.read(DatabasePVNames.IOCS)))
        for name in IOCS:
            self.assertTrue(name in pv_data, msg="{name} in {pv_names}".format(name=name, pv_names=pv_data))

