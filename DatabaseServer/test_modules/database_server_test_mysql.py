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

from mysql_wrapper_tests import generate_fake_db, TEST_DB, HIGH_PV_NAMES, MEDIUM_PV_NAMES
import unittest
from database_server import DatabaseServer
from server_common.mocks.mock_ca_server import MockCAServer
from server_common.utilities import dehex_and_decompress
import os
import json

generate_fake_db(TEST_DB)

class TestDatabaseServer(unittest.TestCase):
    def setUp(self):
        self.ms = MockCAServer()
        self.db_server = DatabaseServer(self.ms, TEST_DB, os.path.abspath('./test_files'), True)
        self.db_server._update_individual_interesting_pvs()

    def test_interest_high_pvs_exist(self):
        on_fly_pvs = self.ms.pv_list
        self.assertTrue("INTERESTING_PVS:TESTIOC:HIGH" in on_fly_pvs.keys())
        self.assertTrue("INTERESTING_PVS:SIMPLE1:HIGH" in on_fly_pvs.keys())
        self.assertTrue("INTERESTING_PVS:SIMPLE2:HIGH" in on_fly_pvs.keys())

    def test_interest_medium_pvs_exist(self):
        on_fly_pvs = self.ms.pv_list
        self.assertTrue("INTERESTING_PVS:TESTIOC:MEDIUM" in on_fly_pvs.keys())
        self.assertTrue("INTERESTING_PVS:SIMPLE1:MEDIUM" in on_fly_pvs.keys())
        self.assertTrue("INTERESTING_PVS:SIMPLE2:MEDIUM" in on_fly_pvs.keys())

    def test_interest_high_pvs_correct(self):
        on_fly_pvs = self.ms.pv_list
        data = [json.loads(dehex_and_decompress(x)) for x in on_fly_pvs.values()]
        pv_names = []
        for item in data:
            if len(item) > 0:
                pv_names.extend([x[0] for x in item])
        for name in HIGH_PV_NAMES:
            self.assertTrue(name in pv_names)

    def test_interest_medium_pvs_correct(self):
        on_fly_pvs = self.ms.pv_list
        data = [json.loads(dehex_and_decompress(x)) for x in on_fly_pvs.values()]
        pv_names = []
        for item in data:
            if len(item) > 0:
                pv_names.extend([x[0] for x in item])
        for name in MEDIUM_PV_NAMES:
            self.assertTrue(name in pv_names)