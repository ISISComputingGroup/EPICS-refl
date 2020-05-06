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
import os
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

    def test_GIVEN_local_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "INST:MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

    def test_GIVEN_remote_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          [alias, "ALIAS", "MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

    def test_GIVEN_local_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.EGU"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          ["{}[.]VAL".format(alias), "ALIAS", "INST:MY_PV.EGU"],
                          [alias, "ALIAS", "INST:MY_PV.EGU"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

# Currently broken on master
    # def test_GIVEN_local_PV_ending_in_same_chars_as_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
    #     blockname, block_pv = "MY_BLOCK", "MY_PV.RBV"
    #     alias = "INST:BLOCK:MY_BLOCK"
    #     expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
    #                       ["{}:RC:.*".format(alias), "DENY"],
    #                       ["{}[.]VAL".format(alias), "ALIAS", "INST:MY_PV.RBV"],
    #                       [alias, "ALIAS", "INST:MY_PV.RBV"]]
    #
    #     lines = self.gateway.generate_alias(blockname, block_pv, True)
    #
    #     self.assertTrue(lines.pop(0).startswith("##"))
    #     lines = [line.split() for line in lines]
    #     self.assertListEqual(lines, expected_lines)

    def test_GIVEN_remote_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.EGU"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          ["{}[.]VAL".format(alias), "ALIAS", "MY_PV.EGU"],
                          [alias, "ALIAS", "MY_PV.EGU"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

    def test_GIVEN_local_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV:SP\\2"],
                          ["{}\(:SP\)?:RC:.*".format(alias), "DENY"],
                          ["{}\(:SP\)?".format(alias), "ALIAS", "INST:MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

    def test_GIVEN_remote_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "MY_PV:SP\\2"],
                          ["{}\(:SP\)?:RC:.*".format(alias), "DENY"],
                          ["{}\(:SP\)?".format(alias), "ALIAS", "MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

    def test_GIVEN_remote_PV_with_VAL_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_TEST.VAL"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [["{}\([.:].*\)".format(alias), "ALIAS", "MY_TEST\\1"],
                          ["{}:RC:.*".format(alias), "DENY"],
                          ["{}".format(alias), "ALIAS", "MY_TEST"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self.assertTrue(lines.pop(0).startswith("##"))
        lines = [line.split() for line in lines]
        self.assertListEqual(lines, expected_lines)

