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
import json
from BlockServer.spangle_banner.banner import Banner
from BlockServer.spangle_banner.bool_str import BoolStr

class TestBannerSequence(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_returns_valid_json(self):
        banner = Banner()
        try:
            json.loads(banner.get_description())
        except:
            self.fail("Invalid JSON received")

    def test_bool_str_constructor_sets_name_and_pv(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        self.assertEqual("test_name", bool_str.get_name())
        self.assertEqual("INSTR:TEST:PV", bool_str.get_pv())

    def test_bool_str_define_true_state_throws_if_dictionary_is_empty(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = dict()
        self.assertRaises(Exception, bool_str.set_true_state, t_state)

    def test_bool_str_does_not_throw_if_true_state_completely_defined(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = dict()
        t_state["message"] = "Test message"
        t_state["colour"] = "RED"
        try:
            bool_str.set_true_state(t_state)
        except:
            self.fail("True state not completely defined")

    def test_bool_str_set_true_state_and_read_back(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = dict()
        t_state["message"] = "Test message"
        t_state["colour"] = "RED"
        bool_str.set_true_state(t_state)

        ans = bool_str.get_true_state()
        self.assertEqual("RED", ans["colour"])
        self.assertEqual("Test message", ans["message"])

    def test_bool_str_does_not_throw_if_false_state_completely_defined(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        f_state = dict()
        f_state["message"] = "Test message"
        f_state["colour"] = "RED"
        try:
            bool_str.set_false_state(f_state)
        except:
            self.fail("False state not completely defined")

    def test_bool_str_set_false_state_and_read_back(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        f_state = dict()
        f_state["message"] = "Test message"
        f_state["colour"] = "RED"
        bool_str.set_false_state(f_state)

        ans = bool_str.get_false_state()
        self.assertEqual("RED", ans["colour"])
        self.assertEqual("Test message", ans["message"])

    def test_bool_str_does_not_throw_if_unknown_state_completely_defined(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        u_state = dict()
        u_state["message"] = "Test message"
        u_state["colour"] = "RED"
        try:
            bool_str.set_unknown_state(u_state)
        except:
            self.fail("Unknown state not completely defined")

    def test_bool_str_set_unknown_state_and_read_back(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        u_state = dict()
        u_state["message"] = "Test message"
        u_state["colour"] = "RED"
        bool_str.set_unknown_state(u_state)

        ans = bool_str.get_unknown_state()
        self.assertEqual("RED", ans["colour"])
        self.assertEqual("Test message", ans["message"])

    def test_bool_str_returns_false_if_not_completely_defined(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        self.assertFalse(bool_str.is_valid())

    def test_bool_str_returns_true_if_completely_defined(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        state = dict()
        state["message"] = "Test message"
        state["colour"] = "RED"
        bool_str.set_true_state(state)
        bool_str.set_false_state(state)
        bool_str.set_unknown_state(state)
        self.assertTrue(bool_str.is_valid())

    def test_bool_str_get_description_equals_what_was_set(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = {"colour": "true_red", "message": "true"}
        f_state = {"colour": "false_red", "message": "false"}
        u_state = {"colour": "unknown_red", "message": "unknown"}
        bool_str.set_true_state(t_state)
        bool_str.set_false_state(f_state)
        bool_str.set_unknown_state(u_state)
        description = bool_str.get_description()
        self.assertEquals("bool_str", description["type"])
        self.assertEquals("test_name", description["name"])
        self.assertEquals("INSTR:TEST:PV", description["pv"])
        self.assertEquals(t_state, description["true_state"])
        self.assertEquals(f_state, description["false_state"])
        self.assertEquals(u_state, description["unknown_state"])

    def test_add_to_banner_and_get_json_is_empty_if_bool_str_is_invalid(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = {"colour": "true_red", "message": "true"}
        f_state = {"colour": "false_red", "message": "false"}
        bool_str.set_true_state(t_state)
        bool_str.set_false_state(f_state)
        banner = Banner()
        banner.add_item(bool_str)
        self.assertEquals(list(), json.loads(banner.get_description()))

    def test_add_to_banner_and_get_json_description_is_correct_if_bool_str_is_valid(self):
        bool_str = BoolStr("test_name", "INSTR:TEST:PV")
        t_state = {"colour": "true_red", "message": "true"}
        f_state = {"colour": "false_red", "message": "false"}
        u_state = {"colour": "unknown_red", "message": "unknown"}
        bool_str.set_true_state(t_state)
        bool_str.set_false_state(f_state)
        bool_str.set_unknown_state(u_state)
        banner = Banner()
        banner.add_item(bool_str)
        ans = json.loads(banner.get_description())
        self.assertEquals(1, len(ans))
        self.assertEquals("true_red", ans[0]["true_state"]["colour"])

if __name__ == '__main__':
    # Run tests
    unittest.main()