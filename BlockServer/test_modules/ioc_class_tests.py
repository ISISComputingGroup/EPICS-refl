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
from BlockServer.config.ioc import IOC


class TestIocClassSequence(unittest.TestCase):
    def test_ioc_to_dict(self):
        ioc = IOC("SIMPLE1")
        macros = {"macro1": {'value': 123}, "macro2": {'value': "Hello"}}
        ioc.macros = macros

        d = ioc.to_dict()
        self.assertTrue("name" in d)
        self.assertTrue("macros" in d)
        macrotest = {"name" : "macro1", "value" : 123}
        self.assertTrue(macrotest in d["macros"])
        macrotest = {"name" : "macro2", "value" : "Hello"}
        self.assertTrue(macrotest in d["macros"])
