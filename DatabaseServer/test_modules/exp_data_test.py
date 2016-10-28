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
from server_common.mocks.mock_ca import MockChannelAccess
from server_common.utilities import dehex_and_decompress
from exp_data import ExpData

class TestExpData(unittest.TestCase):
    def setUp(self):
        self.ca = MockChannelAccess()
        self.exp_data = ExpData("TEST_PREFIX", self.ca, unique_pool=False)

    def decodepv(self, pv):
        return json.loads(dehex_and_decompress(self.ca.caget(pv)))

    def test_single_surname_returns_surname(self):
        # Arrange
        fullname = "Tom Jones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEquals(surname, "Jones")

    def test_double_barrelled_surname_returns_last_name(self):
        # Arrange
        fullname = "Tom de Jones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEquals(surname, "Jones")

    def test_single_name_returns_fullname(self):
        # Arrange
        fullname = "TomJones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEquals(surname, "TomJones")

    def test_update_username_for_single_user(self):
        # Arrange
        users = '[{"name":"Tom Jones","institute":"STFC","role":"user"}]'

        # Act
        self.exp_data.updateUsername(users)

        # Assert
        simnames = self.decodepv(self.exp_data._simnames)
        surnames = self.decodepv(self.exp_data._surnamepv)
        orgs = self.decodepv(self.exp_data._orgspv)

        self.assertEqual(simnames[0]["name"], "Tom Jones")
        self.assertTrue("Jones" in surnames)
        self.assertTrue("STFC" in orgs)

    def test_update_username_for_multiple_users_same_institute(self):
        # Arrange
        users = '['
        users += '{"name":"Tom Jones","institute":"STFC","role":"user"},'
        users += '{"name":"David James","institute":"STFC","role":"user"}'
        users += ']'

        # Act
        self.exp_data.updateUsername(users)

        # Assert
        simnames = self.decodepv(self.exp_data._simnames)
        surnames = self.decodepv(self.exp_data._surnamepv)
        orgs = self.decodepv(self.exp_data._orgspv)

        self.assertEqual(len(simnames), 2)
        self.assertEqual(len(surnames), 2)
        self.assertEqual(len(orgs), 1)

    def test_update_username_for_blank_users(self):
        # Arrange
        users = '[{"name":"Tom Jones","institute":"STFC","role":"user"}]'
        self.exp_data.updateUsername(users)

        # Act
        self.exp_data.updateUsername("")

        # Assert
        simnames = self.decodepv(self.exp_data._simnames)
        surnames = self.decodepv(self.exp_data._surnamepv)
        orgs = self.decodepv(self.exp_data._orgspv)

        self.assertEqual(len(simnames), 0)
        self.assertEqual(len(surnames), 0)
        self.assertEqual(len(orgs), 0)