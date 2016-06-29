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
import os
import shutil

from BlockServer.core.config_list_manager import ConfigListManager, InvalidDeleteException
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.pv_names import BlockserverPVNames
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.mocks.mock_block_server import MockBlockServer
from server_common.utilities import dehex_and_decompress
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.config.configuration import Configuration
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.file_path_manager import FILEPATH_MANAGER


MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

CONFIG_PATH = "./test_configs/"
SCHEMA_PATH = "./../../../../schema"

GET_CONFIG_PV = "GET_CONFIG_DETAILS"
GET_COMPONENT_PV = "GET_COMPONENT_DETAILS"
DEPENDENCIES_PV = "DEPENDENCIES"
CONFIG_CHANGED_PV = ":CURR_CONFIG_CHANGED"

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


class TestInactiveConfigsSequence(unittest.TestCase):

    def setUp(self):
        # Create components folder and copying DEFAULT_COMPONENT fileIO into it
        path = os.path.abspath(CONFIG_PATH)
        FILEPATH_MANAGER.initialise(path)
        self.bs = MockBlockServer()
        self.clm = ConfigListManager(self.bs, SCHEMA_PATH, MockVersionControl())

    # Helper methods
    def _create_config_list_manager(self):
        # The ConfigListManager has to be recreated after any configurations have been created
        # to ensure it picks up the new configs
        self.clm = ConfigListManager(self.bs, SCHEMA_PATH, MockVersionControl())

    def _create_configs(self, names):
        configserver = InactiveConfigHolder(MACROS, MockVersionControl())
        for name in names:
            configserver.save_inactive(name)
        self.clm = ConfigListManager(self.bs, SCHEMA_PATH, MockVersionControl())

    def _create_components(self, names):
        configserver = InactiveConfigHolder(MACROS, MockVersionControl())
        for name in names:
            configserver.save_inactive(name, True)
        self.clm = ConfigListManager(self.bs, SCHEMA_PATH, MockVersionControl())

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(CONFIG_PATH)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_initialisation_with_no_configs_in_directory(self):
        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 0)
        comps = self.clm.get_components()
        self.assertEqual(len(comps), 0)

    def test_initialisation_with_configs_in_directory(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in [c["name"] for c in confs])
        self.assertTrue("TEST_CONFIG2" in [c["name"] for c in confs])

    def test_initialisation_with_components_in_directory(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])
        confs = self.clm.get_components()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_COMPONENT1" in [c["name"] for c in confs])
        self.assertTrue("TEST_COMPONENT2" in [c["name"] for c in confs])

    def test_initialisation_with_configs_in_directory_pv(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])

        self.assertTrue(self.bs.does_pv_exist("TEST_CONFIG1:" + GET_CONFIG_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_CONFIG2:" + GET_CONFIG_PV))
        self.assertFalse(self.bs.does_pv_exist("TEST_CONFIG1:" + GET_COMPONENT_PV))
        self.assertFalse(self.bs.does_pv_exist("TEST_CONFIG2:" + GET_COMPONENT_PV))

    def test_initialisation_with_components_in_directory_pv(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + DEPENDENCIES_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + DEPENDENCIES_PV))
        self.assertFalse(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_CONFIG_PV))
        self.assertFalse(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_CONFIG_PV))

    def test_update_config_from_object(self):
        self.icm = InactiveConfigHolder(MACROS, MockVersionControl())
        self.icm.set_config_details(VALID_CONFIG)
        self.clm.update_a_config_in_list(self.icm)

        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])
        self.assertTrue("TEST_SYNOPTIC" in [conf.get('synoptic') for conf in confs])

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 0)

    def test_update_component_from_object(self):
        self.icm = InactiveConfigHolder(MACROS, MockVersionControl())
        self.icm.set_config_details(VALID_CONFIG)
        self.clm.update_a_config_in_list(self.icm, True)

        confs = self.clm.get_components()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])
        self.assertTrue("TEST_SYNOPTIC" in [conf.get('synoptic') for conf in confs])

        comps = self.clm.get_configs()
        self.assertEqual(len(comps), 0)

    def test_components_json(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])
        comps = self.clm.get_components()
        for comp in comps:
            self.assertEqual(len(comp), 5)
            self.assertTrue("name" in comp)
            self.assertTrue("pv" in comp)
            self.assertTrue("description" in comp)
            self.assertTrue("synoptic" in comp)
            self.assertTrue("history" in comp)
        self.assertTrue("TEST_COMPONENT1" in [comp.get('name') for comp in comps])
        self.assertTrue("TEST_COMPONENT2" in [comp.get('name') for comp in comps])

    def test_pv_of_lower_case_name(self):
        config_name = "test_CONfig1"
        self._test_pv_changed_but_not_name(config_name, "TEST_CONFIG1")

    def test_config_and_component_allowed_same_pv(self):
        self._create_configs(["TEST_CONFIG_AND_COMPONENT1", "TEST_CONFIG_AND_COMPONENT2"])
        self._create_components(["TEST_CONFIG_AND_COMPONENT1", "TEST_CONFIG_AND_COMPONENT2"])

        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 2)

        self.assertTrue("TEST_CONFIG_AND_COMPONENT1" in [m["pv"] for m in confs])
        self.assertTrue("TEST_CONFIG_AND_COMPONENT2" in [m["pv"] for m in confs])

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 2)

        self.assertTrue("TEST_CONFIG_AND_COMPONENT1" in [m["pv"] for m in comps])
        self.assertTrue("TEST_CONFIG_AND_COMPONENT2" in [m["pv"] for m in comps])

    def _test_is_configuration_json(self, data, name):
        self.assertTrue("name" in data)
        self.assertEqual(data["name"], name)
        self.assertTrue("iocs" in data)
        self.assertTrue("blocks" in data)
        self.assertTrue("groups" in data)
        self.assertTrue("description" in data)
        self.assertTrue("synoptic" in data)
        self.assertFalse("pv" in data)

    def _test_pv_changed_but_not_name(self, config_name, expected_pv_name):
        self._create_configs([config_name])
        confs = self.clm.get_configs()

        self.assertEqual(len(confs), 1)
        print "HELLO", self.bs.get_confs()
        self.assertEqual(confs[0]["pv"], expected_pv_name)
        self.assertEqual(confs[0]["name"], config_name)
        self.assertTrue(self.bs.does_pv_exist(expected_pv_name + ":" + GET_CONFIG_PV))
        self.assertFalse(self.bs.does_pv_exist(config_name + ":" + GET_CONFIG_PV))

    def test_delete_configs_empty(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])

        self.clm.active_config_name = "TEST_ACTIVE"
        self.clm.delete_configs([])

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)

    def test_delete_components_empty(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])

        self.clm.active_config_name = "TEST_ACTIVE"
        self.clm.delete_configs([], True)

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_COMPONENT1" in config_names)
        self.assertTrue("TEST_COMPONENT2" in config_names)

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + DEPENDENCIES_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + DEPENDENCIES_PV))

    def test_delete_active_config(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        active = ActiveConfigHolder(MACROS, ArchiverManager(None, None, MockArchiverWrapper()),
                                    MockVersionControl(), MockIocControl(""))
        active.save_active("TEST_ACTIVE")
        self.clm.update_a_config_in_list(active)
        self.clm.active_config_name = "TEST_ACTIVE"

        self._test_none_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_ACTIVE"])
        self._test_none_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_ACTIVE", "TEST_CONFIG1"])
        self._test_none_deleted()
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG1", "TEST_ACTIVE"])
        self._test_none_deleted()

    def test_delete_active_component(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2", "TEST_COMPONENT3"])
        active = ActiveConfigHolder(MACROS, ArchiverManager(None, None, MockArchiverWrapper()),
                                    MockVersionControl(), MockIocControl(""))
        active.add_component("TEST_COMPONENT1", Configuration(MACROS))
        active.save_active("TEST_ACTIVE")
        self.clm.active_config_name = "TEST_ACTIVE"

        self.clm.update_a_config_in_list(active)

        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_COMPONENT1"], True)
        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_COMPONENT1", "TEST_COMPONENT2"], True)
        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG2", "TEST_COMPONENT1"], True)
        self._test_none_deleted(True)

    def test_delete_used_component(self):
        self._create_components(["TEST_COMPONENT3", "TEST_COMPONENT2", "TEST_COMPONENT1"])

        inactive = InactiveConfigHolder(MACROS, MockVersionControl())
        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")

        self.clm.update_a_config_in_list(inactive)
        self.clm.active_config_name = "TEST_ACTIVE"

        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_COMPONENT1"], True)
        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_COMPONENT1", "TEST_COMPONENT2"], True)
        self._test_none_deleted(True)
        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG2", "TEST_COMPONENT1"], True)
        self._test_none_deleted(True)

    def _test_none_deleted(self, is_component=False):
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

    def test_delete_one_config(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])

        self.clm.delete_configs(["TEST_CONFIG1"])
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)

    def test_delete_one_component(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])

        self.clm.delete_configs(["TEST_COMPONENT1"], True)
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertFalse("TEST_COMPONENT1" in config_names)
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + DEPENDENCIES_PV))

    def test_delete_many_configs(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2", "TEST_CONFIG3"])
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

    def test_delete_many_components(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2", "TEST_COMPONENT3"])
        self.clm.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_COMPONENT1" in config_names)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertTrue("TEST_COMPONENT3" in config_names)

        self.clm.delete_configs(["TEST_COMPONENT1", "TEST_COMPONENT3"],  True)

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertFalse("TEST_COMPONENT1" in config_names)
        self.assertFalse("TEST_COMPONENT3" in config_names)
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + DEPENDENCIES_PV))

    def test_delete_config_affects_filesystem(self):
        self._create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertEqual(len(os.listdir(FILEPATH_MANAGER.config_dir)), 2)
        self.clm.delete_configs(["TEST_CONFIG1"])

        configs = os.listdir(FILEPATH_MANAGER.config_dir)
        self.assertEqual(len(configs), 1)
        self.assertTrue("TEST_CONFIG2" in configs)

    def test_delete_component_affects_filesystem(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2"])
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertEqual(len(os.listdir(FILEPATH_MANAGER.component_dir)), 3)
        self.clm.delete_configs(["TEST_COMPONENT1"], True)

        configs = os.listdir(FILEPATH_MANAGER.component_dir)
        self.assertEqual(len(configs), 2)
        self.assertTrue("TEST_COMPONENT2" in configs)

    def test_cant_delete_non_existant_config(self):
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_CONFIG1"])

        config_names = [c["name"] for c in self.clm.get_configs()]
        self.assertEqual(len(config_names), 0)

    def test_cant_delete_non_existant_component(self):
        self.clm.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, ["TEST_COMPONENT1"], True)

        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 0)

    def test_delete_component_after_add_and_remove(self):
        self._create_components(["TEST_COMPONENT1", "TEST_COMPONENT2", "TEST_COMPONENT3"])
        self.clm.active_config_name = "TEST_ACTIVE"

        inactive = InactiveConfigHolder(MACROS, MockVersionControl())

        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update_a_config_in_list(inactive)

        inactive.remove_comp("TEST_COMPONENT1")
        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update_a_config_in_list(inactive)

        self.clm.delete_configs(["TEST_COMPONENT1"], True)
        config_names = [c["name"] for c in self.clm.get_components()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_COMPONENT2" in config_names)
        self.assertTrue("TEST_COMPONENT3" in config_names)
        self.assertFalse("TEST_COMPONENT1" in config_names)

        self.assertTrue(self.bs.does_pv_exist("TEST_INACTIVE:" + GET_CONFIG_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT2:" + DEPENDENCIES_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT3:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT3:" + DEPENDENCIES_PV))

    def test_dependencies_initialises(self):
        self._create_components(["TEST_COMPONENT1"])

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + DEPENDENCIES_PV))

    def test_dependencies_updates_add(self):
        self._create_components(["TEST_COMPONENT1"])
        inactive = InactiveConfigHolder(MACROS, MockVersionControl())

        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update_a_config_in_list(inactive)

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + DEPENDENCIES_PV))

        confs = self.clm.get_configs()
        self.assertEqual(len(confs), 1)
        self.assertEqual("TEST_INACTIVE", confs[0]["name"])

    def test_dependencies_updates_remove(self):
        self._create_components(["TEST_COMPONENT1"])

        inactive = InactiveConfigHolder(MACROS, MockVersionControl())

        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)

        inactive.remove_comp("TEST_COMPONENT1")
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + DEPENDENCIES_PV))

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 1)
        names = [x["name"] for x in comps]
        self.assertFalse("TEST_INACTIVE" in names)

    def test_delete_config_deletes_dependency(self):
        self._create_components(["TEST_COMPONENT1"])
        inactive = InactiveConfigHolder(MACROS, MockVersionControl())
        self.clm.active_config_name = "TEST_ACTIVE"
        inactive.add_component("TEST_COMPONENT1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        self.clm.update_a_config_in_list(inactive)

        self.clm.delete_configs(["TEST_INACTIVE"])

        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))
        self.assertTrue(self.bs.does_pv_exist("TEST_COMPONENT1:" + GET_COMPONENT_PV))

        comps = self.clm.get_components()
        self.assertEqual(len(comps), 1)
        names = [x["name"] for x in comps]
        self.assertFalse("TEST_INACTIVE" in names)

    def test_cannot_delete_default(self):
        self._create_components(["TEST_COMPONENT1"])

        self.assertRaises(InvalidDeleteException, self.clm.delete_configs, [DEFAULT_COMPONENT], True)

    def test_update_inactive_config_from_filewatcher(self):
        inactive = InactiveConfigHolder(MACROS, MockVersionControl())
        self.bs.set_config_list(self.clm)

        inactive.save_inactive("TEST_INACTIVE")
        self.clm.update_a_config_in_list_filewatcher(inactive)

        self.assertEqual(len(self.clm.get_components()), 0)
        self.assertEqual(len(self.clm.get_configs()), 1)
        self.assertTrue("TEST_INACTIVE" in [x['name'] for x in self.clm.get_configs()])
        self.assertEqual(self.clm.get_active_changed(), 0)

    def test_update_inactive_config_from_filewatcher(self):
        inactive = InactiveConfigHolder(MACROS, MockVersionControl())
        self.bs.set_config_list(self.clm)

        inactive.save_inactive("TEST_INACTIVE_COMP", True)
        self.clm.update_a_config_in_list_filewatcher(inactive, True)

        self.assertEqual(len(self.clm.get_components()), 1)
        self.assertEqual(len(self.clm.get_configs()), 0)
        self.assertTrue("TEST_INACTIVE_COMP" in [x['name'] for x in self.clm.get_components()])
        self.assertEqual(self.clm.get_active_changed(), 0)

    def test_update_active_config_from_filewatcher(self):
        active = InactiveConfigHolder(MACROS, MockVersionControl())
        active_config_name = "TEST_ACTIVE"

        self.bs.set_config_list(self.clm)
        self.clm.active_config_name = active_config_name

        active.save_inactive(active_config_name)
        self.clm.update_a_config_in_list_filewatcher(active)

        self.assertEqual(len(self.clm.get_components()), 0)
        self.assertEqual(len(self.clm.get_configs()), 1)
        self.assertTrue("TEST_ACTIVE" in [x['name'] for x in self.clm.get_configs()])
        self.assertEqual(self.clm.get_active_changed(), 1)

    def test_update_active_component_from_filewatcher(self):
        inactive = InactiveConfigHolder(MACROS, MockVersionControl())
        active_config_name = "TEST_ACTIVE"
        active_config_comp = "TEST_ACTIVE_COMP"

        self.bs.set_config_list(self.clm)
        self.clm.active_config_name = active_config_name
        self.clm.active_components = [active_config_comp]

        inactive.save_inactive(active_config_comp, True)
        self.clm.update_a_config_in_list_filewatcher(inactive, True)

        self.assertEqual(len(self.clm.get_components()), 1)
        self.assertEqual(len(self.clm.get_configs()), 0)
        self.assertTrue("TEST_ACTIVE_COMP" in [x['name'] for x in self.clm.get_components()])
        self.assertEqual(self.clm.get_active_changed(), 1)

    def test_default_filtered(self):
        comps = self.clm.get_components()
        self.assertTrue(DEFAULT_COMPONENT not in comps)
