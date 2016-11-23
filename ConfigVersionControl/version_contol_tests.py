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
from config_version_control import ConfigVersionControl, SYSTEM_TEST_PREFIX
from git_version_control import GitVersionControl
from vc_exceptions import NotUnderAllowedBranch
import socket


class MockVersionControl():
    def __init__(self):
        self._files = list()

    def add(self, file_path):
        self._files.append(file_path)


class TestVersionControl(unittest.TestCase):
    def test_WHEN_config_name_contains_rcptt_THEN_do_not_add(self):
        mock_vc = MockVersionControl()
        cfg = ConfigVersionControl(None, mock_vc)
        cfg.add(SYSTEM_TEST_PREFIX + "test")

        self.assertEqual(len(mock_vc._files), 0)

    def test_WHEN_config_name_does_not_contain_rcptt_THEN_add(self):
        mock_vc = MockVersionControl()
        cfg = ConfigVersionControl(None, mock_vc)
        cfg.add("test")

        self.assertEqual(len(mock_vc._files), 1)
        self.assertTrue("test" in mock_vc._files)

    def test_WHEN_banch_is_master_THEN_branch_not_allowed(self):
        self.assertFalse(GitVersionControl.branch_allowed("master"))

    def test_WHEN_banch_is_machine_name_THEN_branch_allowed(self):
        self.assertTrue(GitVersionControl.branch_allowed(socket.gethostname()))

    def test_WHEN_banch_begins_with_nd_THEN_branch_not_allowed(self):
        self.assertFalse(GitVersionControl.branch_allowed("NDTEST"))

    def test_WHEN_banch_begins_contains_nd_THEN_branch_allowed(self):
        self.assertTrue(GitVersionControl.branch_allowed("testNDtest"))