from __future__ import print_function, absolute_import, division, unicode_literals
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
import os
import unittest

import six

from DatabaseServer.options_holder import OptionsHolder
from DatabaseServer.options_loader import OptionsLoader

OPTIONS_PATH = os.path.join(os.path.dirname(__file__), os.path.pardir,  "test_files")


class TestOptionsHolderSequence(unittest.TestCase):

    def test_get_config_options(self):
        oh = OptionsHolder(OPTIONS_PATH, OptionsLoader())

        options = oh.get_config_options()

        self.assertTrue(len(options) > 1, "No options found")
        for n, ioc in six.iteritems(options):
            self.assertTrue(len(ioc) == 3, "Unexpected details in config")
            self.assertTrue("macros" in ioc)
            self.assertTrue("pvsets" in ioc)
            self.assertTrue("pvs" in ioc)

            self.assertTrue(len(ioc["macros"]) > 1)
            self.assertTrue(len(ioc["pvsets"]) > 1)
            self.assertTrue(len(ioc["pvs"]) > 1)

            for macro in ioc["macros"]:
                self.assertTrue("description" in macro)
                self.assertTrue("pattern" in macro)
            for pvset in ioc["pvsets"]:
                self.assertTrue("description" in pvset)
                self.assertTrue("pattern" not in pvset)
            for pv in ioc["pvs"]:
                self.assertTrue("description" in pv)
                self.assertTrue("pattern" not in pv)

