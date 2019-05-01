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

import six
from mock import Mock
from parameterized import parameterized

from BlockServer.config.block import Block
from BlockServer.config.configuration import Configuration
from BlockServer.config.ioc import IOC
from BlockServer.core.active_config_holder import (ActiveConfigHolder, _blocks_changed, _blocks_changed_in_config,
                                                   _compare_ioc_properties)
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from BlockServer.mocks.mock_ioc import MockIoc
from server_common.constants import IS_LINUX


CONFIG_PATH = "./test_configs/"
BASE_PATH = "./example_base/"


# Helper methods
def quick_block_to_json(name, pv, group, local=True):
    return {
        'name': name,
        'pv': pv,
        'group': group,
        'local': local
    }


def add_basic_blocks_and_iocs(config_holder):
    config_holder.add_block(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
    config_holder.add_block(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
    config_holder.add_block(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
    config_holder.add_block(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
    config_holder._add_ioc("SIMPLE1")
    config_holder._add_ioc("SIMPLE2")


def get_groups_and_blocks(jsondata):
    return json.loads(jsondata)


def create_grouping(groups):
    return json.dumps([{"name": group, "blocks": blocks} for group, blocks in six.iteritems(groups)])


def create_dummy_component():
    config = Configuration(MACROS)
    config.add_block("COMPBLOCK1", "PV1", "GROUP1", True)
    config.add_block("COMPBLOCK2", "PV2", "COMPGROUP", True)
    config.add_ioc("COMPSIMPLE1")
    return config


# Note that the ActiveConfigServerManager contains an instance of the Configuration class and hands a lot of
#   work off to this object. Rather than testing whether the functionality in the configuration class works
#   correctly (e.g. by checking that a block has been edited properly after calling configuration.edit_block),
#   we should instead test that ActiveConfigServerManager passes the correct parameters to the Configuration object.
#   We are testing that ActiveConfigServerManager correctly interfaces with Configuration, not testing the
#   functionality of Configuration, which is done in Configuration's own suite of tests.
class TestActiveConfigHolderSequence(unittest.TestCase):

    def setUp(self):
        # Note: All configurations are saved in memory
        self.mock_archive = Mock()
        self.mock_archive.update_archiver = Mock()
        self.mock_file_manager = MockConfigurationFileManager()
        self.active_config_holder = self.create_active_config_holder()

    def create_active_config_holder(self):
        return ActiveConfigHolder(MACROS, self.mock_archive, self.mock_file_manager, MockIocControl(""))

    def test_add_ioc(self):
        config_holder = self.active_config_holder
        iocs = config_holder.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        config_holder._add_ioc("SIMPLE1")
        config_holder._add_ioc("SIMPLE2")
        iocs = config_holder.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    @unittest.skipIf(IS_LINUX, "Unable to save config on Linux")
    def test_save_config(self):
        config_holder = self.active_config_holder
        add_basic_blocks_and_iocs(config_holder)
        try:
            config_holder.save_active("TEST_CONFIG")
        except Exception as e:
            self.fail("test_save_config raised Exception unexpectedly: {}".format(e))

    @unittest.skipIf(IS_LINUX, "Location of last_config.txt not correctly configured on Linux")
    def test_load_config(self):
        config_holder = self.active_config_holder
        add_basic_blocks_and_iocs(config_holder)
        config_holder.save_active("TEST_CONFIG")
        config_holder.clear_config()
        blocks = config_holder.get_blocknames()
        self.assertEquals(len(blocks), 0)
        iocs = config_holder.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        config_holder.load_active("TEST_CONFIG")
        blocks = config_holder.get_blocknames()
        self.assertEquals(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = config_holder.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    @unittest.skipIf(IS_LINUX, "Location of last_config.txt not correctly configured on Linux")
    def test_GIVEN_load_config_WHEN_load_config_again_THEN_no_ioc_changes(self):
        # This test is checking that a load will correctly cache the IOCs that are running so that a comparison will
        # return no change
        config_holder = self.active_config_holder
        add_basic_blocks_and_iocs(config_holder)
        config_holder.save_active("TEST_CONFIG")
        config_holder.clear_config()
        blocks = config_holder.get_blocknames()
        self.assertEquals(len(blocks), 0)
        iocs = config_holder.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        config_holder.load_active("TEST_CONFIG")

        config_holder.load_active("TEST_CONFIG")

        iocs_to_start, iocs_to_restart, iocs_to_stop = config_holder.iocs_changed()
        self.assertEqual(len(iocs_to_start), 0)
        self.assertEqual(len(iocs_to_restart), 0)
        self.assertEqual(len(iocs_to_stop), 0)

    def test_load_notexistant_config(self):
        config_holder = self.active_config_holder
        self.assertRaises(IOError, lambda: config_holder.load_active("DOES_NOT_EXIST"))

    def test_save_as_component(self):
        config_holder = self.active_config_holder
        try:
            config_holder.save_active("TEST_CONFIG1", as_comp=True)
        except Exception as e:
            self.fail("test_save_as_component raised Exception unexpectedly: {}".format(e))

    @unittest.skipIf(IS_LINUX, "Unable to save config on Linux")
    def test_save_config_for_component(self):
        config_holder = self.active_config_holder
        config_holder.save_active("TEST_CONFIG1", as_comp=True)
        try:
            config_holder.save_active("TEST_CONFIG1")
        except Exception as e:
            self.fail("test_save_config_for_component raised Exception unexpectedly: {}".format(e))

    def test_load_component_fails(self):
        config_holder = self.active_config_holder
        add_basic_blocks_and_iocs(config_holder)
        config_holder.save_active("TEST_COMPONENT", as_comp=True)
        config_holder.clear_config()
        self.assertRaises(IOError, lambda: config_holder.load_active("TEST_COMPONENT"))

    @unittest.skipIf(IS_LINUX, "Location of last_config.txt not correctly configured on Linux")
    def test_load_last_config(self):
        config_holder = self.active_config_holder
        add_basic_blocks_and_iocs(config_holder)
        config_holder.save_active("TEST_CONFIG")
        config_holder.clear_config()
        blocks = config_holder.get_blocknames()
        self.assertEqual(len(blocks), 0)
        iocs = config_holder.get_ioc_names()
        self.assertEqual(len(iocs), 0)
        config_holder.load_last_config()
        grps = config_holder.get_group_details()
        self.assertTrue(len(grps) == 3)
        blocks = config_holder.get_blocknames()
        self.assertEqual(len(blocks), 4)
        self.assertTrue('TESTBLOCK1' in blocks)
        self.assertTrue('TESTBLOCK2' in blocks)
        self.assertTrue('TESTBLOCK3' in blocks)
        self.assertTrue('TESTBLOCK4' in blocks)
        iocs = config_holder.get_ioc_names()
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)

    def test_reloading_current_config_with_blank_name_does_nothing(self):
        # arrange
        config_name = self.active_config_holder.get_config_name()
        self.assertEquals(config_name, "")
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

        # act
        self.active_config_holder.reload_current_config()

        # assert
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

    @unittest.skipIf(IS_LINUX, "Location of last_config.txt not correctly configured on Linux")
    def test_reloading_current_config_sends_load_request_correctly(self):
        # arrange
        config_holder = self.active_config_holder
        config_name = "TEST_CONFIG"
        add_basic_blocks_and_iocs(config_holder)
        config_holder.save_active(config_name)

        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(len(load_requests), 0)

        # act
        config_holder.reload_current_config()

        # assert
        load_requests = self.mock_file_manager.get_load_config_history()
        self.assertEquals(load_requests.count(config_name), 1)
        
    def _modify_active(self, config_holder, new_details, name="config1"):
        config = Configuration(MACROS)
        config.meta.name = name
        inactive_config = InactiveConfigHolder(MACROS, self.mock_file_manager)
        inactive_config.set_config_details(new_details)
        inactive_config.save_inactive(name)

        config_holder.load_active(name)

    def test_iocs_changed_no_changes(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()

        self._modify_active(config_holder, details)

        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)
        self.assertEqual(len(stop), 0)

    def test_iocs_changed_ioc_added(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        # Act
        details['iocs'].append(MockIoc())
        self._modify_active(config_holder, details)
        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 1)
        self.assertEqual(len(restart), 0)
        self.assertEqual(len(stop), 0)

    def test_iocs_changed_ioc_removed(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['iocs'].append(MockIoc())
        self._modify_active(config_holder, details)
        # Act
        details['iocs'].pop(0)
        self._modify_active(config_holder, details)
        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)
        self.assertEqual(len(stop), 1)

    def test_GIVEN_an_ioc_defined_in_a_component_WHEN_the_component_is_removed_THEN_the_ioc_is_stopped(self):

        # Arrange
        config_holder = self.create_active_config_holder()

        component = create_dummy_component()
        component.iocs = {"DUMMY_IOC": IOC("dummyname")}

        self.mock_file_manager.comps["component_name"] = component
        config_holder.add_component("component_name", component)
        self._modify_active(config_holder, config_holder.get_config_details())

        # Act
        config_holder.remove_comp("component_name")

        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)
        self.assertEqual(len(stop), 1)

    def test_GIVEN_an_ioc_defined_in_the_top_level_config_WHEN_the_ioc_is_removed_THEN_the_ioc_is_stopped(self):

        # Arrange
        config_holder = self.create_active_config_holder()

        details = config_holder.get_config_details()
        details['iocs'].append(MockIoc())
        self._modify_active(config_holder, details)

        # Act
        details['iocs'].pop(0)
        self._modify_active(config_holder, details)

        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)
        self.assertEqual(len(stop), 1)

    def test_given_empty_config_when_block_added_then_blocks_changed_returns_true(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        # Act
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Assert
        self.assertTrue(config_holder.blocks_changed())

    def test_given_config_when_block_params_changed_then_blocks_changed_returns_true(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        details['blocks'][0]['local'] = False
        self._modify_active(config_holder, details)
        # Assert
        self.assertTrue(config_holder.blocks_changed())

    def test_given_config_with_one_block_when_block_removed_then_blocks_changed_returns_true(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        details['blocks'].pop(0)
        self._modify_active(config_holder, details)
        # Assert
        self.assertTrue(config_holder.blocks_changed())

    def test_given_empty_config_when_component_added_then_blocks_changed_returns_true(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        # Act
        config_holder.add_component(name="TESTCOMPONENT", component=create_dummy_component())
        # Assert
        self.assertTrue(config_holder.blocks_changed())

    def test_given_empty_config_when_no_change_then_blocks_changed_returns_false(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        # Act
        self._modify_active(config_holder, details)
        # Assert
        self.assertFalse(config_holder.blocks_changed())

    def test_given_config_when_no_change_then_blocks_changed_returns_false(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        self._modify_active(config_holder, details)
        # Assert
        self.assertFalse(config_holder.blocks_changed())

    def test_given_no_blocks_changed_when_update_archiver_archiver_not_restarted(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        self._modify_active(config_holder, details)
        config_holder.update_archiver()
        # Assert
        self.assertFalse(self.mock_archive.update_archiver.called)

    def test_given_blocks_changed_when_update_archiver_archiver_is_restarted(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        details['blocks'].append(Block(name="TESTNAME2", pv="TESTPV2").to_dict())
        self._modify_active(config_holder, details)
        config_holder.update_archiver()
        # Assert
        self.assertTrue(self.mock_archive.update_archiver.called)

    def test_given_no_blocks_changed_but_full_init_when_update_archiver_archiver_is_restarted(self):
        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()
        details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(config_holder, details)
        # Act
        self._modify_active(config_holder, details)
        config_holder.update_archiver(True)
        # Assert
        self.assertTrue(self.mock_archive.update_archiver.called)

    def _test_attribute_changes(self, initial_attrs=None, final_attrs=None, has_changed=True):
        # Take a dict of initial attributes and final attributes and
        # check for the correct change response.

        if initial_attrs is None:
            initial_attrs = {}

        if final_attrs is None:
            final_attrs = {}

        # Arrange
        config_holder = self.create_active_config_holder()
        details = config_holder.get_config_details()

        initial_ioc = MockIoc()
        for key, value in initial_attrs.iteritems():
            setattr(initial_ioc, key, value)
        final_ioc = MockIoc()
        for key, value in final_attrs.iteritems():
            setattr(final_ioc, key, value)

        details['iocs'].append(initial_ioc)
        self._modify_active(config_holder, details)
        # Act
        details['iocs'][0] = final_ioc
        self._modify_active(config_holder, details)
        # Assert
        start, restart, stop = config_holder.iocs_changed()
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 1 if has_changed else 0)
        self.assertEqual(len(stop), 0)

    def test_iocs_changed_macro_added(self):
        self._test_attribute_changes(final_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST"}]})

    def test_iocs_changed_macro_removed(self):
        self._test_attribute_changes(initial_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST"}]})

    def test_iocs_changed_macro_changed(self):
        self._test_attribute_changes(initial_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST"}]},
                                     final_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST_NEW"}]})

    def test_iocs_changed_macro_not_changed(self):
        self._test_attribute_changes(initial_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST"}]},
                                     final_attrs={'macros': [{"name": "TESTMACRO1", "value": "TEST"}]},
                                     has_changed=False)

    def test_iocs_changed_pvs_added(self):
        self._test_attribute_changes(final_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]})

    def test_iocs_changed_pvs_removed(self):
        self._test_attribute_changes(initial_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]})

    def test_iocs_changed_pvs_changed(self):
        self._test_attribute_changes(initial_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]},
                                     final_attrs={'pvs': [{"name": "TESTPV1", "value": 456}]})

    def test_iocs_not_changed_pvs_not_changed(self):
        self._test_attribute_changes(initial_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]},
                                     final_attrs={'pvs': [{"name": "TESTPV1", "value": 123}]},
                                     has_changed=False)

    def test_iocs_changed_pvsets_added(self):
        self._test_attribute_changes(final_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]})

    def test_iocs_changed_pvsets_removed(self):
        self._test_attribute_changes(initial_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]})

    def test_iocs_changed_pvsets_changed(self):
        self._test_attribute_changes(initial_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]},
                                     final_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": False}]})

    def test_iocs_not_changed_pvsets_not_changed(self):
        self._test_attribute_changes(initial_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]},
                                     final_attrs={'pvsets': [{"name": "TESTPVSET1", "enabled": True}]},
                                     has_changed=False)

    def test_iocs_changed_simlevel_added(self):
        self._test_attribute_changes(final_attrs={'simlevel': 'recsim'})

    def test_iocs_changed_simlevel_removed(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'})

    def test_iocs_changed_simlevel_changed(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'},
                                     final_attrs={'simlevel': 'devsim'})

    def test_iocs_not_changed_simlevel_unchanged(self):
        self._test_attribute_changes(initial_attrs={'simlevel': 'recsim'},
                                     final_attrs={'simlevel': 'recsim'},
                                     has_changed=False)

    @parameterized.expand([
        (Block(name="name", pv="pv"), Block(name="other", pv="pv")),
        (Block(name="name", pv="pv"), Block(name="name", pv="other")),
        (Block(name="name", pv="pv", local=True), Block(name="name", pv="pv", local=False)),
        (Block(name="name", pv="pv", component="A"), Block(name="name", pv="pv", component="B")),
        (Block(name="name", pv="pv", runcontrol=True), Block(name="name", pv="pv", runcontrol=False)),
        (Block(name="name", pv="pv", lowlimit=True), Block(name="name", pv="pv", lowlimit=False)),
        (Block(name="name", pv="pv", highlimit=True), Block(name="name", pv="pv", highlimit=False)),
        (Block(name="name", pv="pv", log_periodic=True), Block(name="name", pv="pv", log_periodic=False)),
        (Block(name="name", pv="pv", log_rate=True), Block(name="name", pv="pv", log_rate=False)),
        (Block(name="name", pv="pv", log_deadband=True), Block(name="name", pv="pv", log_deadband=False)),
    ])
    def test_WHEN_block_attributes_different_THEN_blocks_changed_returns_true(self, block1, block2):
        self.assertTrue(_blocks_changed(block1, block2))

    def test_WHEN_block_attributes_different_THEN_blocks_changed_returns_false(self):
        self.assertFalse(_blocks_changed(Block(name="name", pv="pv"), Block(name="name", pv="pv")))

    def test_WHEN_blocks_changed_in_config_called_for_configs_which_contain_same_blocks_THEN_returns_false(self):
        config1 = Mock()
        config1.blocks = {"a": Block(name="a", pv="pv")}

        config2 = Mock()
        config2.blocks = {"a": Block(name="a", pv="pv")}

        self.assertFalse(_blocks_changed_in_config(config1, config2))

    def test_WHEN_blocks_changed_in_config_called_for_configs_with_removed_blocks_THEN_returns_true(self):
        config1 = Mock()
        config1.blocks = {"a": Block(name="a", pv="pv")}

        config2 = Mock()
        config2.blocks = {}

        self.assertTrue(_blocks_changed_in_config(config1, config2))

    def test_WHEN_blocks_changed_in_config_called_for_configs_with_added_blocks_THEN_returns_true(self):
        config1 = Mock()
        config1.blocks = {}

        config2 = Mock()
        config2.blocks = {"a": Block(name="a", pv="pv")}

        self.assertTrue(_blocks_changed_in_config(config1, config2))

    def test_WHEN_blocks_changed_in_config_called_and_block_comparator_says_they_are_different_THEN_returns_true(self):
        config1 = Mock()
        config1.blocks = {"a": Block(name="a", pv="pv")}

        config2 = Mock()
        config2.blocks = {"a": Block(name="a", pv="pv")}

        self.assertTrue(_blocks_changed_in_config(config1, config2, block_comparator=lambda block1, block2: True))

    def test_WHEN_blocks_changed_in_config_called_and_block_comparator_says_they_are_the_same_THEN_returns_false(self):
        config1 = Mock()
        config1.blocks = {"a": Block(name="a", pv="pv")}

        config2 = Mock()
        config2.blocks = {"a": Block(name="a", pv="pv")}

        self.assertFalse(_blocks_changed_in_config(config1, config2, block_comparator=lambda block1, block2: False))

    def test_WHEN_compare_ioc_properties_called_with_the_same_ioc_then_returns_empty_set_of_iocs_to_start_restart(self):
        old_config = Mock()
        old_config.iocs = {"a": MockIoc("a")}

        new_config = Mock()
        new_config.iocs = {"a": MockIoc("a")}

        start, restart = _compare_ioc_properties(old_config, new_config)
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 0)

    @parameterized.expand([
        ({"a": MockIoc("a", macros=True)}, {"a": MockIoc("a", macros=False)}),
        ({"a": MockIoc("a", pvs=True)}, {"a": MockIoc("a", pvs=False)}),
        ({"a": MockIoc("a", pvsets=True)}, {"a": MockIoc("a", pvsets=False)}),
        ({"a": MockIoc("a", simlevel=True)}, {"a": MockIoc("a", simlevel=False)}),
        ({"a": MockIoc("a", restart=True)}, {"a": MockIoc("a", restart=False)}),
    ])
    def test_WHEN_compare_ioc_properties_called_with_different_then_restarts_ioc(self, old_iocs, new_iocs):
        old_config = Mock()
        old_config.iocs = old_iocs

        new_config = Mock()
        new_config.iocs = new_iocs

        start, restart = _compare_ioc_properties(old_config, new_config)
        self.assertEqual(len(start), 0)
        self.assertEqual(len(restart), 1)

    def test_WHEN_compare_ioc_properties_called_with_new_ioc_then_starts_new_ioc(self):
        old_config = Mock()
        old_config.iocs = {}

        new_config = Mock()
        new_config.iocs = {"a": MockIoc("a", macros=True)}

        start, restart = _compare_ioc_properties(old_config, new_config)
        self.assertEqual(len(start), 1)
        self.assertEqual(len(restart), 0)


if __name__ == '__main__':
    # Run tests
    unittest.main()
