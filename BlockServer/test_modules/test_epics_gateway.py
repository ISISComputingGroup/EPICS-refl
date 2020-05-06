# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2020 Science & Technology Facilities Council.
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
from mock import patch, MagicMock

from BlockServer.epics.gateway import Gateway


class TestEpicsGateway(unittest.TestCase):

    def setUp(self):
        self.gateway_prefix = "GATEWAY:"
        self.block_prefix = "BLOCK:"
        self.gateway_file_path = "FILE_PATH"
        self.prefix = "INST:"

        self.gateway = Gateway(self.gateway_prefix, self.block_prefix, self.gateway_file_path, self.prefix)

    @patch("BlockServer.epics.gateway.ChannelAccess")
    def test_GIVEN_gateway_pv_doesnt_exist_WHEN_exist_called_THEN_returns_false(self, channel_access):
        channel_access.caget = MagicMock(return_value=None)
        self.assertFalse(self.gateway.exists())
        channel_access.caget.assert_called_with(self.gateway_prefix + "pvtotal")

    @patch("BlockServer.epics.gateway.ChannelAccess")
    def test_GIVEN_gateway_pv_exists_WHEN_exist_called_THEN_returns_true(self, channel_access):
        channel_access.caget = MagicMock(return_value="Hi")
        self.assertTrue(self.gateway.exists())
        channel_access.caget.assert_called_with(self.gateway_prefix + "pvtotal")

    def _assert_lines_correct(self, actual_lines, expected_lines):
        sanitised_lines = list()
        for line in actual_lines:
            if not line.startswith("##") and line != "":
                sanitised_lines.append(line.split())

        self.assertListEqual(sanitised_lines, expected_lines)

    def test_GIVEN_local_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "INST:MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.EGU"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          ["{}[.]VAL".format(alias), "ALIAS", "INST:MY_PV.EGU"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "INST:MY_PV.EGU"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.RBV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}[.]VAL".format(alias), "ALIAS", "MY_PV.RBV"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "MY_PV.RBV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV:SP\\2"],
                          [r"{}\(:SP\)?:RC:.*".format(alias), "DENY"],
                          [r"{}\(:SP\)?".format(alias), "ALIAS", "INST:MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "MY_PV:SP\\2"],
                          [r"{}\(:SP\)?:RC:.*".format(alias), "DENY"],
                          [r"{}\(:SP\)?".format(alias), "ALIAS", "MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_VAL_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_TEST.VAL"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_TEST\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          ["{}".format(alias), "ALIAS", "MY_TEST"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_lowercase_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "My_Block", "MY_PV"
        alias = "INST:BLOCK:My_Block"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "MY_PV"],
                          [r"{}\([.:].*\)".format(alias.upper()), "ALIAS", "MY_PV\\1"],
                          ["{}:RC:.*".format(alias.upper()), "DENY"],
                          [alias.upper(), "ALIAS", "MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)
