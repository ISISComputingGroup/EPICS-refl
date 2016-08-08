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
from BlockServer.core.ioc_control import IocControl, IOCS_NOT_TO_STOP
from BlockServer.mocks.mock_procserv_utils import MockProcServWrapper


class TestIocControlSequence(unittest.TestCase):
    def test_start_ioc_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc("TESTIOC")
        self.assertEqual(ic.get_ioc_status("TESTIOC"), "RUNNING")

    def test_stop_ioc_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc("TESTIOC")
        ic.stop_ioc("TESTIOC")
        self.assertEqual(ic.get_ioc_status("TESTIOC"), "SHUTDOWN")

    def test_restart_ioc_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc("TESTIOC")
        ic.restart_ioc("TESTIOC")
        self.assertEqual(ic.get_ioc_status("TESTIOC"), "RUNNING")

    def test_stop_ioc_on_not_allowed_to_stop(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc(IOCS_NOT_TO_STOP[0])
        ic.stop_ioc(IOCS_NOT_TO_STOP[0])
        self.assertEqual(ic.get_ioc_status(IOCS_NOT_TO_STOP[0]), "RUNNING")

    def test_restart_ioc_on_not_allowed_to_stop(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc(IOCS_NOT_TO_STOP[0])
        ic.restart_ioc(IOCS_NOT_TO_STOP[0])
        self.assertEqual(ic.get_ioc_status(IOCS_NOT_TO_STOP[0]), "RUNNING")

    def test_start_iocs_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(ic.get_ioc_status("TESTIOC1"), "RUNNING")
        self.assertEqual(ic.get_ioc_status("TESTIOC2"), "RUNNING")

    def test_stop_iocs_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        ic.stop_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(ic.get_ioc_status("TESTIOC1"), "SHUTDOWN")
        self.assertEqual(ic.get_ioc_status("TESTIOC2"), "SHUTDOWN")

    def test_restart_iocs_and_get_ioc_status(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        ic.restart_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(ic.get_ioc_status("TESTIOC1"), "RUNNING")
        self.assertEqual(ic.get_ioc_status("TESTIOC2"), "RUNNING")

    def test_ioc_exists(self):
        ic = IocControl("", MockProcServWrapper())
        self.assertTrue(ic.ioc_exists("TESTIOC"))

    def test_set_autorestart_works(self):
        ic = IocControl("", MockProcServWrapper())
        ic.start_ioc("TESTIOC")
        ic.set_autorestart("TESTIOC", True)
        self.assertEqual(ic.get_autorestart("TESTIOC"), True)
        ic.set_autorestart("TESTIOC", False)
        self.assertEqual(ic.get_autorestart("TESTIOC"), False)
