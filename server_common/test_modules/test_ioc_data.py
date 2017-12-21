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

import unittest
from DatabaseServer.mocks.mock_procserv_utils import MockProcServWrapper
from server_common.ioc_data import IOCData


TEST_DB = 'test_iocdb'
HIGH_PV_NAMES = ["HIGH_PV1", "HIGH_PV2", "HIGH_PV3"]
MEDIUM_PV_NAMES = ["MED_PV1", "MED_PV2", "MED_PV3"]
FACILITY_PV_NAMES = ["FAC_PV1", "FAC_PV2", "FAC_PV3"]
BL_PVS = ["PARS:BL:FOEMIRROR", "PARS:BL:A1", "PARS:BL:CHOPEN:ANG"]
SAMPLE_PVS = ["PARS:SAMPLE:AOI", "PARS:SAMPLE:GEOMETRY", "PARS:SAMPLE:WIDTH"]
USER_PVS = ["PARS:USER:PV1", "PARS:USER:PV2", "PARS:USER:PV3"]


class MockIocDataSource(object):
    def __init__(self):
        self.iocs = {
            "TESTIOC": {"description": "test ioc", "running": False},
            "SIMPLE1": {"description": "simple ioc 1", "running": False},
            "SIMPLE2": {"description": "simple ioc 2", "running": False}
        }

    def get_iocs_and_descriptions(self):
        return self.iocs

    def get_iocs_and_running_status(self):
        d = []
        for k, v in self.iocs.iteritems():
            d.append((k, v["running"]))
        return d

    def update_ioc_is_running(self, iocname, running):
        self.iocs[iocname]["running"] = running

    def get_interesting_pvs(self, level="", ioc=None):
        # In the real thing each PV is a tuple containing name, ioc, interest level etc.
        # For testing we don't need to worry about that
        pvs = []
        if level == "" or level.lower().startswith('h'):
            pvs.extend(HIGH_PV_NAMES)
        if level == "" or level.lower().startswith('m'):
            pvs.extend(MEDIUM_PV_NAMES)
        if level == "" or level.lower().startswith('f'):
            pvs.extend(FACILITY_PV_NAMES)
        return pvs

    def get_active_pvs(self):
        return HIGH_PV_NAMES

    def get_pars(self, category):
        if category == 'BEAMLINEPAR':
            return BL_PVS
        elif category == 'SAMPLEPAR':
            return SAMPLE_PVS
        elif category == 'USERPAR':
            return USER_PVS


class TestIocDataSequence(unittest.TestCase):
    def setUp(self):
        self.prefix = ""
        self.ioc_source = MockIocDataSource()
        self.proc_server = MockProcServWrapper()
        self.ioc_data = IOCData(self.ioc_source, self.proc_server, self.prefix)

    def test_iocs_are_reported_as_not_running_if_stopped(self):
        # Arrange
        self.proc_server.stop_ioc(self.prefix, "TESTIOC")

        # Action
        self.ioc_data.update_iocs_status()
        iocs = self.ioc_data.get_iocs()

        # Assert
        self.assertEqual(iocs["TESTIOC"]["running"], False)

    def test_iocs_are_reported_as_running_if_set_running(self):
        # Arrange
        self.proc_server.start_ioc(self.prefix, "TESTIOC")

        # Action
        self.ioc_data.update_iocs_status()
        iocs = self.ioc_data.get_iocs()

        # Assert
        self.assertEqual(iocs["TESTIOC"]["running"], True)
        self.assertEqual(iocs["SIMPLE1"]["running"], False)
        self.assertEqual(iocs["SIMPLE2"]["running"], False)

    def test_get_interesting_pvs_all(self):
        # Get all PVs
        pvs = self.ioc_data.get_interesting_pvs()

        all_names = HIGH_PV_NAMES
        all_names.extend(MEDIUM_PV_NAMES)
        all_names.extend(FACILITY_PV_NAMES)

        # Check all pvs are in all names
        for pv in pvs:
            self.assertTrue(pv in all_names)

    def test_get_interesting_pvs_high(self):
        # Get all PVs
        pvs = self.ioc_data.get_interesting_pvs("HIGH")

        for pv in pvs:
            self.assertTrue(pv in HIGH_PV_NAMES)

    def test_get_interesting_pvs_medium(self):
        # Get all PVs
        pvs = self.ioc_data.get_interesting_pvs("MEDIUM")
        for pv in pvs:
            self.assertTrue(pv in MEDIUM_PV_NAMES)

    def test_get_interesting_pvs_facility(self):
        # Get all PVs
        pvs = self.ioc_data.get_interesting_pvs("FACILITY")
        for pv in pvs:
            self.assertTrue(pv in FACILITY_PV_NAMES)

    def test_get_active_pvs(self):
        # Get all Active PVs
        pvs = self.ioc_data.get_active_pvs()
        for pv in pvs:
            self.assertTrue(pv in HIGH_PV_NAMES)

    def test_get_beamline_pars(self):
        pars = self.ioc_data.get_beamline_pars()
        self.assertEqual(len(pars), len(BL_PVS))
        for n in BL_PVS:
            self.assertTrue(n in pars)

    def test_get_sample_pars(self):
        pars = self.ioc_data.get_sample_pars()
        self.assertEqual(len(pars), len(SAMPLE_PVS))
        for n in SAMPLE_PVS:
            self.assertTrue(n in pars)

    def test_get_user_pars(self):
        pars = self.ioc_data.get_user_pars()
        self.assertEqual(len(pars), len(USER_PVS))
        for n in USER_PVS:
            self.assertTrue(n in pars)

    def test_get_active_iocs_returns_running_iocs_when_one_is_running(self):
        # Arrange
        self.proc_server.start_ioc(self.prefix, "TESTIOC")

        # Action
        self.ioc_data.update_iocs_status()
        active = self.ioc_data.get_active_iocs()

        # Assert
        self.assertEqual(1, len(active))
        self.assertTrue("TESTIOC" in active)

    def test_get_active_iocs_returns_empty_when_none_are_running(self):
        # Arrange

        # Action
        self.ioc_data.update_iocs_status()
        active = self.ioc_data.get_active_iocs()

        # Assert
        self.assertEqual(0, len(active))
