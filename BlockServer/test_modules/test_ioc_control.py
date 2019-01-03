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
from BlockServer.core.ioc_control import IocControl
from BlockServer.mocks.mock_procserv_utils import MockProcServWrapper
from server_common.constants import IOCS_NOT_TO_STOP
from mock import patch


class TestIocControlSequence(unittest.TestCase):
    @patch("BlockServer.core.ioc_control.ProcServWrapper", MockProcServWrapper)
    def setUp(self):
        self.ic = IocControl("")

    def test_start_ioc_and_get_ioc_status(self):
        self.ic.start_ioc("TESTIOC")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC"), "RUNNING")

    def test_stop_ioc_and_get_ioc_status(self):
        self.ic.start_ioc("TESTIOC")
        self.ic.stop_ioc("TESTIOC")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC"), "SHUTDOWN")

    def test_restart_ioc_and_get_ioc_status(self):
        self.ic.start_ioc("TESTIOC")
        self.ic.restart_ioc("TESTIOC")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC"), "RUNNING")

    def test_stop_ioc_on_not_allowed_to_stop(self):
        self.ic.start_ioc(IOCS_NOT_TO_STOP[0])
        self.ic.stop_ioc(IOCS_NOT_TO_STOP[0])
        self.assertEqual(self.ic.get_ioc_status(IOCS_NOT_TO_STOP[0]), "RUNNING")

    def test_restart_ioc_on_not_allowed_to_stop(self):
        self.ic.start_ioc(IOCS_NOT_TO_STOP[0])
        self.ic.restart_ioc(IOCS_NOT_TO_STOP[0])
        self.assertEqual(self.ic.get_ioc_status(IOCS_NOT_TO_STOP[0]), "RUNNING")

    def test_start_iocs_and_get_ioc_status(self):
        self.ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(self.ic.get_ioc_status("TESTIOC1"), "RUNNING")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC2"), "RUNNING")

    def test_stop_iocs_and_get_ioc_status(self):
        self.ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        self.ic.stop_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(self.ic.get_ioc_status("TESTIOC1"), "SHUTDOWN")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC2"), "SHUTDOWN")

    def test_restart_iocs_and_get_ioc_status(self):
        self.ic.start_iocs(["TESTIOC1", "TESTIOC2"])
        self.ic.restart_iocs(["TESTIOC1", "TESTIOC2"])
        self.assertEqual(self.ic.get_ioc_status("TESTIOC1"), "RUNNING")
        self.assertEqual(self.ic.get_ioc_status("TESTIOC2"), "RUNNING")

    def test_ioc_exists(self):
        self.assertTrue(self.ic.ioc_exists("TESTIOC"))

    def test_set_autorestart_works(self):
        self.ic.start_ioc("TESTIOC")
        self.ic.set_autorestart("TESTIOC", True)
        self.assertEqual(self.ic.get_autorestart("TESTIOC"), True)
        self.ic.set_autorestart("TESTIOC", False)
        self.assertEqual(self.ic.get_autorestart("TESTIOC"), False)

    def test_WHEN_ioc_restart_requested_THEN_ioc_control_may_return_before_restart_complete(self):
        self.ic.start_ioc("TESTIOC")
        self.assertFalse(self.ic.ioc_restart_pending("TESTIOC"))
        self.ic.restart_ioc("TESTIOC")
        self.assertTrue(self.ic.ioc_restart_pending("TESTIOC"))

    def test_GIVEN_reapply_auto_default_WHEN_ioc_restarts_requested_THEN_ioc_control_may_return_before_restart_complete(self):
        self.ic.start_ioc("TESTIOC")
        self.assertFalse(self.ic.ioc_restart_pending("TESTIOC"))
        self.ic.restart_iocs(["TESTIOC"])
        self.assertTrue(self.ic.ioc_restart_pending("TESTIOC"))

    def test_GIVEN_reapply_auto_true_WHEN_multiple_ioc_restarts_requested_THEN_ioc_control_waits_for_restart_complete(self):
        self.ic.start_ioc("TESTIOC")
        self.assertFalse(self.ic.ioc_restart_pending("TESTIOC"))
        self.ic.restart_iocs(["TESTIOC"], reapply_auto=True)
        self.assertFalse(self.ic.ioc_restart_pending("TESTIOC"))
