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
import typing
import unittest
import json
from server_common.mocks.mock_ca import MockChannelAccess
from server_common.utilities import dehex_and_decompress
from DatabaseServer.exp_data import ExpData


class MockExpDataSource(object):
    def __init__(self):
        self.valid_experiments = {"123456": [["Matt", "ESS", "PI"], ["Dom", "ISIS", ""], ["Jack", "ISIS", "Contact"]]}

    def experiment_exists(self, experiment_id):
        return experiment_id in self.valid_experiments

    def get_team(self, experiment_id):
        return self.valid_experiments[experiment_id]


class TestExpData(unittest.TestCase):
    def setUp(self):
        self.ca = MockChannelAccess()
        self.mock_data_source = MockExpDataSource()
        self.exp_data = ExpData("TEST_PREFIX", self.mock_data_source, self.ca)

    def decode_pv(self, pv: str) -> typing.Any:
        return json.loads(dehex_and_decompress(self.ca.caget(pv)))

    def test_update_experiment_id_set_surnames_if_experiment_exists_but_skips_contact(self):
        self.exp_data.update_experiment_id("123456")
        data = self.ca.caget(self.exp_data._daenamespv)
        self.assertEqual(b"Matt,Dom", data)

    def test_update_experiment_id_set_surnames_pv(self):
        self.exp_data.update_experiment_id("123456")
        data = self.decode_pv(self.exp_data._surnamepv)
        self.assertIsInstance(data, list)
        self.assertCountEqual(data, ["Matt", "Dom"])

    def test_update_experiment_id_set_orgs_pv(self):
        self.exp_data.update_experiment_id("123456")
        data = self.decode_pv(self.exp_data._orgspv)
        self.assertIsInstance(data, list)
        self.assertCountEqual(data, ["ESS", "ISIS"])

    def test_update_experiment_id_throws_if_experiment_does_not_exists(self):
        try:
            self.exp_data.update_experiment_id("000000")
            self.fail("Setting invalid experiment id did not throw")
        except:
            pass

    def test_single_surname_returns_surname(self):
        # Arrange
        fullname = "Tom Jones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEqual(surname, "Jones")

    def test_double_barrelled_surname_returns_last_name(self):
        # Arrange
        fullname = "Tom de Jones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEqual(surname, "Jones")

    def test_single_name_returns_fullname(self):
        # Arrange
        fullname = "TomJones"

        # Act
        surname = self.exp_data._get_surname_from_fullname(fullname)

        # Assert
        self.assertEqual(surname, "TomJones")

    def test_update_username_for_single_user(self):
        # Arrange
        users = '[{"name":"Tom Jones","institute":"STFC","role":"user"}]'

        # Act
        self.exp_data.update_username(users)

        # Assert
        simnames = self.decode_pv(self.exp_data._simnames)
        surnames = self.decode_pv(self.exp_data._surnamepv)
        orgs = self.decode_pv(self.exp_data._orgspv)

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
        self.exp_data.update_username(users)

        # Assert
        simnames = self.decode_pv(self.exp_data._simnames)
        surnames = self.decode_pv(self.exp_data._surnamepv)
        orgs = self.decode_pv(self.exp_data._orgspv)

        self.assertEqual(len(simnames), 2)
        self.assertEqual(len(surnames), 2)
        self.assertEqual(len(orgs), 1)

    def test_update_username_for_blank_users(self):
        # Arrange
        users = '[{"name":"Tom Jones","institute":"STFC","role":"user"}]'
        self.exp_data.update_username(users)

        # Act
        self.exp_data.update_username("")

        # Assert
        simnames = self.decode_pv(self.exp_data._simnames)
        surnames = self.decode_pv(self.exp_data._surnamepv)
        orgs = self.decode_pv(self.exp_data._orgspv)

        self.assertEqual(len(simnames), 0)
        self.assertEqual(len(surnames), 0)
        self.assertEqual(len(orgs), 0)

    def test_remove_accents_from_name(self):
        # Arrange
        # list of names in unicode code points, which is the same as ISO-8859-1 encoding 
        names_uni = [u'Somebody', u'S\xf8rina', u'\xe9\xe5\xf5\xf6\xc6']
        # best ascii equivalents of names 
        names_ascii = [b'Somebody', b'Sorina', b'eaooAE']

        # Act
        conv_names = ExpData.make_name_list_ascii(names_uni).split(b',')

        # Assert
        self.assertEqual(conv_names, names_ascii)
