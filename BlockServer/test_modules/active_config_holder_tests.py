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

from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from BlockServer.mocks.mock_ioc import MockIoc


CONFIG_PATH = "./test_configs/"
BASE_PATH = "./example_base/"


# Helper methods
def quick_block_to_json(name, pv, group, local=True):
    data = {'name': name, 'pv': pv, 'group': group, 'local': local}
    return data

def add_block(cs, data):
    cs.add_block(data)

def add_basic_blocks_and_iocs(cs):
    add_block(cs, quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
    add_block(cs, quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
    add_block(cs, quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
    add_block(cs, quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
    cs._add_ioc("SIMPLE1")
    cs._add_ioc("SIMPLE2")

def get_groups_and_blocks(jsondata):
    groups = json.loads(jsondata)
    return groups

def create_grouping(groups):
    struct = []
    for grp, blocks in groups.iteritems():
        d = dict()
        d["name"] = grp
        d["blocks"] = blocks
        struct.append(d)    
    ans = json.dumps(struct)
    return ans


# Note that the ActiveConfigServerManager contains an instance of the Configuration class and hands a lot of
#   work off to this object. Rather than testing whether the functionality in the configuration class works
#   correctly (e.g. by checking that a block has been edited properly after calling configuration.edit_block),
#   we should instead test that ActiveConfigServerManager passes the correct parameters to the Configuration object.
#   We are testing that ActiveConfigServerManager correctly interfaces with Configuration, not testing the
#   functionality of Configuration, which is done in Configuration's own suite of tests.
class TestActiveConfigHolderSequence(unittest.TestCase):

    def setUp(self):
        # Note: All configurations are saved in memory
        self.mock_archive = ArchiverManager(None, None, MockArchiverWrapper())
        self.mock_file_manager = MockConfigurationFileManager()
        self.activech = ActiveConfigHolder(MACROS, self.mock_archive, MockVersionControl(),
                                           self.mock_file_manager, MockIocControl(""))

    def tearDown(self):
        pass

    def create_ach(self):
        ch = ActiveConfigHolder(MACROS, self.mock_archive, MockVersionControl(), MockConfigurationFileManager(),
                                MockIocControl(""))
        return ch

    def test_add_ioc(self):
        cs = self.activech
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs._add_ioc("SIMPLE1")
        cs._add_ioc("SIMPLE2")
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_save_config(self):
        cs = self.activech
        add_basic_blocks_and_iocs(cs)
        try:
            cs.save_active("TEST_CONFIG")
        except Exception:
            self.fail("test_save_config raised Exception unexpectedly!")

    def test_load_config(self):
        cs = self.activech
        add_basic_blocks_and_iocs(cs)
        cs.save_active("TEST_CONFIG")
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEquals(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_active("TEST_CONFIG")
        blocks = cs.get_blocknames()
        self.assertEquals(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_load_notexistant_config(self):
        cs = self.activech
        self.assertRaises(IOError, lambda: cs.load_active("DOES_NOT_EXIST"))

    def test_save_as_component(self):
        cs = self.activech
        try:
            cs.save_active("TEST_CONFIG1", as_comp=True)
        except Exception:
            self.fail("test_save_as_component raised Exception unexpectedly!")

    def test_save_config_for_component(self):
        cs = self.activech
        cs.save_active("TEST_CONFIG1", as_comp=True)
        try:
            cs.save_active("TEST_CONFIG1")
        except Exception:
            self.fail("test_save_config_for_component raised Exception unexpectedly!")

    def test_load_component_fails(self):
        cs = self.activech
        add_basic_blocks_and_iocs(cs)
        cs.save_active("TEST_COMPONENT", as_comp=True)
        cs.clear_config()
        self.assertRaises(IOError, lambda: cs.load_active("TEST_COMPONENT"))

    def test_load_last_config(self):
        cs = self.activech
        add_basic_blocks_and_iocs(cs)
        cs.save_active("TEST_CONFIG")
        cs.clear_config()
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 0)
        iocs = cs.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        cs.load_last_config()
        grps = cs.get_group_details()
        self.assertTrue(len(grps) == 3)
        blocks = cs.get_blocknames()
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = cs.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_reloading_current_config_with_blank_name_does_nothing(self):
        # arrange
        config_name = self.activech.get_config_name()
        self.assertEquals(config_name, "")
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

        # act
        self.activech.reload_current_config()

        # assert
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

    def test_reloading_current_config_sends_load_request_correctly(self):
        # arrange
        cs = self.activech
        config_name = "TEST_CONFIG"
        add_basic_blocks_and_iocs(cs)
        cs.save_active(config_name)

        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

        # act
        cs.reload_current_config()

        # assert
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(load_requests.count(config_name), 1)

    def test_iocs_changed_no_changes(self):
        # Arrange
        ch = self.create_ach()
        details = ch.get_config_details()
        ch.set_config_details(details)
        # Assert
        start, restart = ch.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)

    def test_iocs_changed_ioc_added(self):
        # Arrange
        ch = self.create_ach()
        details = ch.get_config_details()
        # Act
        details['iocs'].append(MockIoc())
        ch.set_config_details(details)
        # Assert
        start, restart = ch.iocs_changed()
        self.assertEqual(len(start), 1)
        self.assertEqual(len(restart), 0)

    def test_iocs_changed_ioc_removed(self):
        # Arrange
        ch = self.create_ach()
        details = ch.get_config_details()
        details['iocs'].append(MockIoc())
        ch.set_config_details(details)
        # Act
        details['iocs'].pop(0)
        ch.set_config_details(details)
        # Assert
        start, restart = ch.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)

    def _test_attribute_changes(self, initial_attrs={}, final_attrs={}, has_changed=True):
        # Take a dict of initial attributes and final attributes and
        # check for the correct change response.

        # Arrange
        ch = self.create_ach()
        details = ch.get_config_details()

        initial_ioc = MockIoc()
        for key, value in initial_attrs.iteritems():
            setattr(initial_ioc, key, value)
        final_ioc = MockIoc()
        for key, value in final_attrs.iteritems():
            setattr(final_ioc, key, value)

        details['iocs'].append(initial_ioc)
        ch.set_config_details(details)
        # Act
        details['iocs'][0] = final_ioc
        ch.set_config_details(details)
        # Assert
        start, restart = ch.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 1 if has_changed else 0)

    def test_iocs_changed_macro_added(self):
        self._test_attribute_changes(final_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST"}]})

    def test_iocs_changed_macro_removed(self):
        self._test_attribute_changes(initial_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST"}]})

    def test_iocs_changed_macro_changed(self):
        self._test_attribute_changes(initial_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST"}]},
                                     final_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST_NEW"}]})

    def test_iocs_changed_macro_not_changed(self):
        self._test_attribute_changes(initial_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST"}]},
                                     final_attrs={'macros':[{"name": "TESTMACRO1", "value": "TEST"}]},
                                     has_changed=False)

    def test_iocs_changed_pvs_added(self):
        self._test_attribute_changes(final_attrs={'pvs':[{"name": "TESTPV1", "value": 123}]})

    def test_iocs_changed_pvs_removed(self):
        self._test_attribute_changes(initial_attrs={'pvs':[{"name": "TESTPV1", "value": 123}]})

    def test_iocs_changed_pvs_changed(self):
        self._test_attribute_changes(initial_attrs={'pvs':[{"name": "TESTPV1", "value": 123}]},
                                     final_attrs={'pvs': [{"name": "TESTPV1", "value": 456}]})

    def test_iocs_not_changed_pvs_not_changed(self):
        self._test_attribute_changes(initial_attrs={'pvs':[{"name": "TESTPV1", "value": 123}]},
                                     final_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]},
                                     has_changed=False)

    def test_iocs_changed_pvsets_added(self):
        self._test_attribute_changes(final_attrs={'pvsets':[{"name": "TESTPVSET1", "enabled": True}]})

    def test_iocs_changed_pvsets_removed(self):
        self._test_attribute_changes(initial_attrs={'pvsets':[{"name": "TESTPVSET1", "enabled": True}]})

    def test_iocs_changed_pvsets_changed(self):
        self._test_attribute_changes(initial_attrs={'pvsets':[{"name": "TESTPVSET1", "enabled": True}]},
                                     final_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": False}]})

    def test_iocs_not_changed_pvsets_not_changed(self):
        self._test_attribute_changes(initial_attrs={'pvsets':[{"name": "TESTPVSET1", "enabled": True}]},
                                     final_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]},
                                     has_changed=False)

    def test_iocs_changed_simlevel_added(self):
        self._test_attribute_changes(final_attrs={'simlevel':'recsim'})

    def test_iocs_changed_simlevel_removed(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'})

    def test_iocs_changed_simlevel_changed(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'},
                                     final_attrs={'simlevel': 'devsim'})

    def test_iocs_not_changed_simlevel_unchanged(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'},
                                     final_attrs={'simlevel': 'recsim'},
                                     has_changed=False)

if __name__ == '__main__':
    # Run tests
    unittest.main()
