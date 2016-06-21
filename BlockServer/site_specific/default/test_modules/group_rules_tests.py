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
from BlockServer.site_specific.default.general_rules import GroupRules
from BlockServer.core.pv_names import BlockserverPVNames
from server_common.mocks.mock_ca_server import MockCAServer
import unittest
import json
import re
from server_common.utilities import dehex_and_decompress


class TestGroupRulesSequence(unittest.TestCase):
    """ Unit tests for block rules, note that changes here may have to be propagated to clients """

    def setUp(self):
        self.cas = MockCAServer()
        self.group_rules = GroupRules(self.cas)

    def get_block_rules_json(self):
        pv_key = BlockserverPVNames.GROUP_RULES
        return json.loads(dehex_and_decompress(self.cas.pv_list.get(pv_key)))

    def get_regex(self):
        regex_string = self.get_block_rules_json().get("regex")
        return re.compile(regex_string)

    def test_block_rules_pv(self):
        self.assertTrue(BlockserverPVNames.GROUP_RULES in self.cas.pv_list)

    def test_disallowed_in_json(self):
        self.assertTrue("disallowed" in self.get_block_rules_json())
        disallowed_list = self.get_block_rules_json().get("disallowed")
        self.assertTrue(isinstance(disallowed_list, list))

    def test_regex_in_json(self):
        self.assertTrue("regex" in self.get_block_rules_json())

    def test_regex_message_in_json(self):
        self.assertTrue("regexMessage" in self.get_block_rules_json())

    def test_regex_lowercase_valid(self):
        self.assertTrue(self.get_regex().match("abc"))

    def test_regex_underscore_valid(self):
        self.assertTrue(self.get_regex().match("abc_"))

    def test_regex_uppercase_valid(self):
        regex = self.get_regex()
        self.assertTrue(regex.match("ABC"))

    def test_regex_numbers_valid(self):
        self.assertTrue(self.get_regex().match("abc1"))

    def test_regex_start_with_number_invalid(self):
        self.assertFalse(self.get_regex().match("1abc"))

    def test_regex_start_with_underscore_invalid(self):
        self.assertFalse(self.get_regex().match("_abc"))

    def test_regex_blank_invalid(self):
        self.assertFalse(self.get_regex().match(""))

    def test_regex_special_chars_invalid(self):
        self.assertFalse(self.get_regex().match("abc@"))