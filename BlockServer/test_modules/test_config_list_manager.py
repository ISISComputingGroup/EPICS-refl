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

from BlockServer.core.config_list_manager import ConfigListManager, InvalidDeleteException
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.mocks.mock_channel_access import MockChannelAccess
from server_common.pv_names import BlockserverPVNames, prepend_blockserver
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.config.configuration import Configuration
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from server_common.utilities import create_pv_name

CONFIG_PATH = "./test_configs/"
SCHEMA_PATH = "./../../../../schema"

GET_CONFIG_PV = ":GET_CONFIG_DETAILS"
GET_COMPONENT_PV = ":GET_COMPONENT_DETAILS"
DEPENDENCIES_PV = ":DEPENDENCIES"

VALID_CONFIG = {
        "iocs": [{
            "simlevel": "None",
            "autostart": True,
            "restart": False,
            "pvsets": [{"name": "SET", "value": "true"}],
            "pvs": [{"name": "A_PV", "value": "TEST"}],
            "macros": [{"name": "A_MACRO", "value": "TEST"}],
            "name": "AN_IOC",
            "component": None}],
        "blocks": [{
            "name": "TEST_BLOCK",
            "local": True,
            "pv": "NDWXXX:xxxx:TESTPV",
            "component": None,
            "visible": True}],
        "components": [],
        "groups": [{
            "blocks": ["TEST_BLOCK"], "name": "TEST_GROUP", "component": None}],
        "name": "TEST_CONFIG",
        "description": "A Test Configuration",
        "synoptic": "TEST_SYNOPTIC"}


def create_dummy_config(name="DUMMY"):
    config = Configuration(MACROS)
    config.add_block("TESTBLOCK1", "PV1", "GROUP1", True)
    config.add_block("TESTBLOCK2", "PV2", "GROUP2", True)
    config.add_block("TESTBLOCK3", "PV3", "GROUP2", True)
    config.add_block("TESTBLOCK4", "PV4", "NONE", False)
    config.add_ioc("SIMPLE1")
    config.add_ioc("SIMPLE2")
    config.set_name(name)
    return config


def create_dummy_component(name="DUMMY"):
    config = Configuration(MACROS)
    config.add_block("COMPBLOCK1", "PV1", "GROUP1", True)
    config.add_block("COMPBLOCK2", "PV2", "COMPGROUP", True)
    config.add_ioc("COMPSIMPLE1")
    config.set_name(name)
    return config


class TestInactiveConfigsSequence(unittest.TestCase):

    def setUp(self):
        self.bs = MockBlockServer()
        self.file_manager = MockConfigurationFileManager()
        self.mock_channel_access = MockChannelAccess()
        self.mock_channel_access.caput(MACROS["$(MYPVPREFIX)"] + "CS:MANAGER", "Yes")
        self.clm = ConfigListManager(self.bs, SCHEMA_PATH, self.file_manager, channel_access=self.mock_channel_access)

    def tearDown(self):
        pass

    # Helper methods
    def _create_inactive_config_holder(self):
        configserver = InactiveConfigHolder(MACROS, self.file_manager)
        return configserver

    def _does_pv_exist(self, name):
        fullname = self._correct_pv_name(name)
        return self.bs.does_pv_exist(fullname)

    def _correct_pv_name(self, name):
        return prepend_blockserver(name)

    def _create_configs(self, names, clm):
        configserver = self._create_inactive_config_holder()
        for name in names:
            conf = create_dummy_config(name)
            configserver.set_config(conf)
            configserver.save_inactive(name)
            clm.update_a_config_in_list(configserver)

    def _create_components(self, names):
        configserver = self._create_inactive_config_holder()
        for name in names:
            conf = create_dummy_component(name)
            configserver.set_config(conf, True)
            configserver.save_inactive(name, True)
            self.clm.update_a_config_in_list(configserver, True)

    def _create_pvs(self, pv_names, suffix=""):
        pvs = list()
        for name in pv_names:
            pvs.append(create_pv_name(name, pvs, "DEFAULT"))

        pvs = [pv + suffix for pv in pvs]
        return pvs

    def _check_no_configs_deleted(self, is_component=False):
        if is_component:
            config_names = [c["name"] for c in self.clm.get_components()]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_COMPONENT1" in config_names)
            self.assertTrue("TEST_COMPONENT2" in config_names)
            self.assertTrue("TEST_COMPONENT3" in config_names)
        else:
            config_names = [c["name"] for c in self.clm.get_configs()]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_CONFIG2" in config_names)
            self.assertTrue("TEST_CONFIG1" in config_names)
            self.assertTrue("TEST_ACTIVE" in config_names)

    def _check_pv_changed_but_not_name(self, config_name, expected_pv_name):
        self._create_configs([config_name], self.clm)
        confs = self.clm.get_configs()

        self.assertEqual(len(confs), 1)
        self.assertEqual(confs[0]["pv"], expected_pv_name)
        self.assertEqual(confs[0]["name"], config_name)

        self.assertTrue(self._does_pv_exist(expected_pv_name + GET_CONFIG_PV))
        self.assertFalse(self._does_pv_exist(config_name + GET_CONFIG_PV))

    # Tests
    def test_initialisation_with_no_configs(self):
        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 0)
        comps = self.clm.get_components()
        self.assertEqual(len(comps), 0)

    def test_initialisation_with_configs(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"], self.clm)
        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in [c["name"] for c in confs])
        self.assertTrue("TEST_CONFIG2" in [c["name"] for c in confs])

    def test_initialisation_with_components(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])
        confs = self.clm.get_components()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_COMPONENT1" in [c["name"] for c in confs])
        self.assertTrue("TEST_COMPONENT2" in [c["name"] for c in confs])

    def test_initialisation_with_configs_creates_pvs(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"], self.clm)

        pvs = self._create_pvs(["TEST_CONFIG1", "TEST_CONFIG2"], GET_CONFIG_PV)
        pvs += self._create_pvs(["TEST_CONFIG1", "TEST_CONFIG2"], GET_COMPONENT_PV)

        for pv in pvs[:2]:
            self.assertTrue(self._does_pv_exist(pv))
        for pv in pvs[2:]:
            self.assertFalse(self._does_pv_exist(pv))

    def test_initialisation_with_components_creates_pv(self):
        comps = ["TEST_COMPONENT1", "TEST_COMPONENT2"]
        self._create_components(comps)

        pvs = self._create_pvs(comps, GET_COMPONENT_PV)
        pvs += self._create_pvs(comps, DEPENDENCIES_PV)
        pvs += self._create_pvs(comps, GET_CONFIG_PV)

        for pv in pvs[:4]:
            self.assertTrue(self._does_pv_exist(pv))
        for pv in pvs[4:]:
            self.assertFalse(self._does_pv_exist(pv))

    def test_update_config_from_object(self):
        self.icm = self._create_inactive_config_holder()
        self.icm.set_config_details(VALID_CONFIG)
        self.clm.update_a_config_in_list(self.icm)

        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue(create_pv_name("TEST_CONFIG", [], "") in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])
        self.assertTrue("TEST_SYNOPTIC" in [conf.get('synoptic') for conf in confs])

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 0)

    def test_add_a_new_component_to_list(self):
        self.icm = self._create_inactive_config_holder()
        self.icm.set_config_details(VALID_CONFIG)
        self.clm.update_a_config_in_list(self.icm, True)

        confs = self.clm.get_components()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue(create_pv_name("TEST_CONFIG", [], "") in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])
        self.assertTrue("TEST_SYNOPTIC" in [conf.get('synoptic') for conf in confs])

        comps = self.clm.get_configs()
        self.assertEqual(len(comps), 0)

    def test_add_multiple_components(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])
        comps = self.clm.get_components()
        for comp in comps:
            self.assertEqual(len(comp), 6)
            self.assertTrue("name" in comp)
            self.assertTrue("pv" in comp)
            self.assertTrue("description" in comp)
            self.assertTrue("synoptic" in comp)
            self.assertTrue("history" in comp)
            self.assertTrue("isProtected" in comp)
        self.assertTrue("TEST_COMPONENT1" in [comp.get('name') for comp in comps])
        self.assertTrue("TEST_COMPONENT2" in [comp.get('name') for comp in comps])

    def test_pv_of_lower_case_name(self):
        config_name = "test_CONfig1"
        self._check_pv_changed_but_not_name(config_name, create_pv_name(config_name, [], ""))

    def test_config_and_component_allowed_same_pv(self):
        self._create_configs(["TEST_CONFIG_AND_COMPONENT1", "TEST_CONFIG_AND_COMPONENT2"], self.clm)
        self._create_components(["TEST_CONFIG_AND_COMPONENT1", "TEST_CONFIG_AND_COMPONENT2"])

        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 2)

        pvs = self._create_pvs(["TEST_CONFIG_AND_COMPONENT1", "TEST_CONFIG_AND_COMPONENT2"], "")

        self.assertTrue(pvs[0] in [m["pv"] for m in confs])
        self.assertTrue(pvs[1] in [m["pv"] for m in confs])

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 2)

        self.assertTrue(pvs[0] in [m["pv"] for m in comps])
        self.assertTrue(pvs[1] in [m["pv"] for m in comps])

    def test_delete_configs_with_empty_list_does_nothing(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"], self.clm)

        self.clm.active_config_name = "TEST_ACTIVE"
        self.clm.delete_configs([])

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)

    def test_delete_components_with_empty_list_does_nothing(self):
        comp_names = ["TEST_COMPONENT1", "TEST_COMPONENT2"]
        self._create_components(comp_names)

        self.clm.active_config_name = "TEST_ACTIVE"
        self.clm.delete_configs([])

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue(comp_names[0] in config_names)
        self.assertTrue(comp_names[1] in config_names)

        pvs = self._create_pvs(comp_names, GET_COMPONENT_PV)
        pvs += self._create_pvs(comp_names, DEPENDENCIES_PV)

        for pv in pvs:
            self.assertTrue(self._does_pv_exist(pv))

    def test_delete_active_config_throws(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"], self.clm)
        active = ActiveConfigHolder(MACROS, ArchiverManager(None, None, MockArchiverWrapper()), self.file_manager,
                                    MockIocControl(""))
        active.save_active("TEST_ACTIVE")
        self.clm.update_a_config_in_list(active)
        self.clm.active_config_name = "TEST_ACTIVE"

        self._check_no_configs_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_ACTIVE"])
        self._check_no_configs_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_ACTIVE", "TEST_CONFIG1"])
        self._check_no_configs_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG1", "TEST_ACTIVE"])
        self._check_no_configs_deleted()

    def test_delete_active_component_throws(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2", "TEST_COMPONENT3"])
        active = ActiveConfigHolder(MACROS, ArchiverManager(None, None, MockArchiverWrapper()), self.file_manager,
                                    MockIocControl(""))
        active.add_component("TEST_COMPONENT1", Configuration(MACROS))
        active.save_active("TEST_ACTIVE")
        self.clm.active_config_name = "TEST_ACTIVE"

        self.clm.update_a_config_in_list(active)

        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_COMPONENT1"])
        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_COMPONENT1", "TEST_COMPONENT2"])
        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_CONFIG2", "TEST_COMPONENT1"])
        self._check_no_configs_deleted(True)

    def test_delete_used_component_throws(self):
        self._create_components(["TEST_COMPONENT3", "TEST_COMPONENT2", "TEST_COMPONENT1"])

        inactive = self._create_inactive_config_holder()
        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")

        self.clm.update_a_config_in_list(inactive)
        self.clm.active_config_name = "TEST_ACTIVE"

        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_COMPONENT1"])
        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_COMPONENT1", "TEST_COMPONENT2"])
        self._check_no_configs_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_CONFIG2", "TEST_COMPONENT1"])
        self._check_no_configs_deleted(True)

    def test_delete_one_inactive_config_works(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"], self.clm)

        self.clm.delete_configs(["TEST_CONFIG1"])
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)

    def test_delete_one_inactive_component_works(self):
        comps = ["TEST_COMPONENT1", "TEST_COMPONENT2"]
        self._create_components(comps)

        self.clm.delete_components(["TEST_COMPONENT1"])
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertFalse("TEST_COMPONENT1" in config_names)

        pvs = self._create_pvs(comps, GET_COMPONENT_PV)
        pvs += self._create_pvs(comps, DEPENDENCIES_PV)
        self.assertFalse(self._does_pv_exist(pvs[0]))
        self.assertTrue(self._does_pv_exist(pvs[1]))
        self.assertFalse(self._does_pv_exist(pvs[2]))
        self.assertTrue(self._does_pv_exist(pvs[3]))

    def test_delete_many_inactive_configs_works(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2", "TEST_CONFIG3"], self.clm)
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertTrue("TEST_CONFIG3" in config_names)

        self.clm.delete_configs(["TEST_CONFIG1", "TEST_CONFIG3"])
        config_names = [c["name"] for c in self.clm.get_configs()]

        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)
        self.assertFalse("TEST_CONFIG3" in config_names)

    def test_delete_many_inactive_components_works(self):
        all_comp_names = ["TEST_COMPONENT1", "TEST_COMPONENT2", "TEST_COMPONENT3"]
        self._create_components(all_comp_names)
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_COMPONENT1" in config_names)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertTrue("TEST_COMPONENT3" in config_names)

        self.clm.delete_components(["TEST_COMPONENT2", "TEST_COMPONENT3"])

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_COMPONENT1" in config_names)
        self.assertFalse("TEST_COMPONENT2" in config_names)
        self.assertFalse("TEST_COMPONENT3" in config_names)

        pvs = self._create_pvs(all_comp_names, GET_COMPONENT_PV)
        pvs += self._create_pvs(all_comp_names, DEPENDENCIES_PV)

        self.assertTrue(self._does_pv_exist(pvs[0]))
        self.assertTrue(self._does_pv_exist(pvs[3]))
        self.assertFalse(self._does_pv_exist(pvs[1]))
        self.assertFalse(self._does_pv_exist(pvs[2]))
        for pv in pvs[4:]:
            self.assertFalse(self._does_pv_exist(pv))

    def test_cant_delete_non_existent_config(self):
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG1"])

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 0)

    def test_cant_delete_non_existent_component(self):
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, self.clm.delete_components, ["TEST_COMPONENT1"])

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 0)

    def test_required_pvs_are_created(self):
        comp_names = ["TEST_COMPONENT1"]
        self._create_components(comp_names)

        pvs = self._create_pvs(comp_names, GET_COMPONENT_PV)
        pvs += self._create_pvs(comp_names, DEPENDENCIES_PV)

        for pv in pvs:
            self.assertTrue(self._does_pv_exist(pv))

    def test_required_pvs_are_deleted_when_component_deleted(self):
        comp_names = ["TEST_COMPONENT1"]
        self._create_components(comp_names)
        pvs = self._create_pvs(comp_names, GET_COMPONENT_PV)
        pvs += self._create_pvs(comp_names, DEPENDENCIES_PV)

        for pv in pvs:
            self.assertTrue(self._does_pv_exist(pv))

        self.clm.delete_components(comp_names)

        for pv in pvs:
            self.assertFalse(self._does_pv_exist(pv))

    def test_dependencies_updates_when_component_added_to_config(self):
        self._create_components(["TEST_COMPONENT1"])
        inactive = self._create_inactive_config_holder()
        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update_a_config_in_list(inactive)
        self.assertTrue("TEST_INACTIVE" in self.clm.get_dependencies("TEST_COMPONENT1"))

    def test_dependencies_updates_when_component_added_to_multiple_configs(self):
        self._create_components(["TEST_COMPONENT1"])
        config1 = self._create_inactive_config_holder()
        config1.add_component("TEST_COMPONENT1", Configuration(MACROS))
        config1.save_inactive("TEST_CONFIG1")
        config2 = self._create_inactive_config_holder()
        config2.add_component("TEST_COMPONENT1", Configuration(MACROS))
        config2.save_inactive("TEST_CONFIG2")
        self.clm.update_a_config_in_list(config1)
        self.clm.update_a_config_in_list(config2)
        self.assertTrue("TEST_CONFIG1" in self.clm.get_dependencies("TEST_COMPONENT1"))
        self.assertTrue("TEST_CONFIG2" in self.clm.get_dependencies("TEST_COMPONENT1"))

    def test_dependencies_updates_remove(self):
        self._create_components(["TEST_COMPONENT1"])

        inactive = self._create_inactive_config_holder()

        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)

        inactive.remove_comp("TEST_COMPONENT1")
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)

        self.assertFalse("TEST_INACTIVE" in self.clm.get_dependencies("TEST_COMPONENT1"))

    def test_delete_config_deletes_dependency(self):
        self._create_components(["TEST_COMPONENT1"])

        inactive = self._create_inactive_config_holder()
        self.clm.active_config_name = "TEST_ACTIVE"
        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)
        self.clm.delete_configs(["TEST_INACTIVE"])
        self.assertFalse("TEST_INACTIVE" in self.clm.get_dependencies("TEST_COMPONENT1"))

    def test_cannot_delete_default(self):
        self._create_components(["TEST_COMPONENT1"])

        self.assertRaises(InvalidDeleteException, self.clm.delete_components, [DEFAULT_COMPONENT])

    def test_update_inactive_config_from_filewatcher(self):
        inactive = self._create_inactive_config_holder()
        self.bs.set_config_list(self.clm)

        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update(inactive)

        self.assertEqual(len(self.clm.get_components()), 0)
        self.assertEqual(len(self.clm.get_configs()), 1)
        self.assertTrue("TEST_INACTIVE" in [x['name'] for x in self.clm.get_configs()])

    def test_update_inactive_component_from_filewatcher(self):
        inactive = self._create_inactive_config_holder()
        self.bs.set_config_list(self.clm)

        inactive.save_inactive("TEST_INACTIVE_COMP", True)
        self.clm.update(inactive, True)

        self.assertEqual(len(self.clm.get_components()), 1)
        self.assertEqual(len(self.clm.get_configs()), 0)
        self.assertTrue("TEST_INACTIVE_COMP" in [x['name'] for x in self.clm.get_components()])

    def test_update_active_config_from_filewatcher(self):
        active = self._create_inactive_config_holder()
        active_config_name = "TEST_ACTIVE"

        self.bs.set_config_list(self.clm)
        self.clm.active_config_name = active_config_name

        active.save_inactive(active_config_name)
        self.clm.update(active)

        self.assertEqual(len(self.clm.get_components()), 0)
        self.assertEqual(len(self.clm.get_configs()), 1)
        self.assertTrue("TEST_ACTIVE" in [x['name'] for x in self.clm.get_configs()])

    def test_update_active_component_from_filewatcher(self):
        inactive = self._create_inactive_config_holder()
        active_config_name = "TEST_ACTIVE"
        active_config_comp = "TEST_ACTIVE_COMP"

        self.bs.set_config_list(self.clm)
        self.clm.active_config_name = active_config_name
        self.clm.active_components = [active_config_comp]

        inactive.save_inactive(active_config_comp, True)
        self.clm.update(inactive, True)

        self.assertEqual(len(self.clm.get_components()), 1)
        self.assertEqual(len(self.clm.get_configs()), 0)
        self.assertTrue("TEST_ACTIVE_COMP" in [x['name'] for x in self.clm.get_components()])

    def test_default_filtered(self):
        comps = self.clm.get_components()
        self.assertTrue(DEFAULT_COMPONENT not in comps)
