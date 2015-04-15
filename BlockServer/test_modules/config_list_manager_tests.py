import unittest
import json
import os
import shutil

from BlockServer.core.config_list_manager import ConfigListManager, InvalidDeleteException
from BlockServer.core.active_config_holder import ActiveConfigHolder
from server_common.mocks.mock_ca_server import MockCAServer
from BlockServer.mocks.mock_block_server import MockBlockServer
from server_common.utilities import dehex_and_decompress
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY, DEFAULT_COMPONENT
from BlockServer.config.configuration import Configuration
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl


MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

CONFIG_PATH = "./test_configs/"
SCHEMA_PATH = "./../../../schema"

GET_CONFIG_PV = "GET_CONFIG_DETAILS"
GET_SUBCONFIG_PV = "GET_COMPONENT_DETAILS"
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
            "subconfig": None}],
        "blocks": [{
            "name": "TEST_BLOCK",
            "local": True,
            "pv": "NDWXXX:xxxx:TESTPV",
            "subconfig": None,
            "visible": True}],
        "components": [],
        "groups": [{
            "blocks": ["TEST_BLOCK"], "name": "TEST_GROUP", "subconfig": None}],
        "name": "TEST_CONFIG",
        "description": "A Test Configuration"}


def create_configs(names):
        configserver = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        for name in names:
            configserver.save_inactive(name)


def create_subconfigs(names):
        configserver = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        for name in names:
            configserver.save_inactive(name, True)
        return configserver


class TestInactiveConfigsSequence(unittest.TestCase):

    def setUp(self):
        # Create components folder and copying DEFAULT_COMPONENT fileIO into it
        path = os.path.abspath(CONFIG_PATH)
        self.ms = MockCAServer()
        self.bs = MockBlockServer()

    def _create_ic(self):
        return ConfigListManager(self.bs, CONFIG_PATH, self.ms, SCHEMA_PATH, MockVersionControl(), test_mode=True)

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(CONFIG_PATH)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_initialisation_with_no_configs_in_directory(self):
        ic = self._create_ic()
        confs = ic.get_configs()
        self.assertEqual(len(confs), 0)
        subconfs = ic.get_subconfigs()
        self.assertEqual(len(subconfs), 0)

    def test_initialisation_with_configs_in_directory(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = self._create_ic()
        confs = ic.get_configs()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in [c["name"] for c in confs])
        self.assertTrue("TEST_CONFIG2" in [c["name"] for c in confs])

    def test_initialisation_with_subconfigs_in_directory(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = self._create_ic()
        confs = ic.get_subconfigs()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_SUBCONFIG1" in [c["name"] for c in confs])
        self.assertTrue("TEST_SUBCONFIG2" in [c["name"] for c in confs])

    def test_initialisation_with_configs_in_directory_pv(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        self._create_ic()
        ms = self.ms

        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_CONFIG1:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_CONFIG2:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())

    def test_initialisation_with_subconfigs_in_directory_pv(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        self._create_ic()
        ms = self.ms

        self.assertEqual(len(ms.pv_list), 5)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG1:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG2:" + GET_CONFIG_PV in ms.pv_list.keys())

    def test_initialisation_pv_config_data(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        self._create_ic()
        ms = self.ms
        data = ms.pv_list.get("TEST_CONFIG1:" + GET_CONFIG_PV)
        data = json.loads(dehex_and_decompress(data))

        self.assertTrue("name" in data)
        self.assertEqual(data["name"], "TEST_CONFIG1")
        self._test_is_configuration_json(data, "TEST_CONFIG1")

    def test_initialisation_pv_config_data(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        self._create_ic()
        ms = self.ms
        data = ms.pv_list.get("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV)
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_SUBCONFIG1")

    def test_update_config_from_object(self):
        ics = self._create_ic()
        ic = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl())
        ic.set_config_details(VALID_CONFIG)
        ics.update_a_config_in_list(ic)

        confs = ics.get_configs()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = ics.get_subconfigs()
        self.assertEqual(len(subconfs), 0)

    def test_update_subconfig_from_object(self):
        ics = self._create_ic()
        ic = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl())
        ic.set_config_details(VALID_CONFIG)
        ics.update_a_config_in_list(ic, True)

        confs = ics.get_subconfigs()
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = ics.get_configs()
        self.assertEqual(len(subconfs), 0)

    def test_subconfigs_json(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = self._create_ic()
        confs = ic.get_subconfigs()
        for conf in confs:
            self.assertEqual(len(conf), 4)
            self.assertTrue("name" in conf)
            self.assertTrue("pv" in conf)
            self.assertTrue("description" in conf)
            self.assertTrue("history" in conf)
        self.assertTrue("TEST_SUBCONFIG1" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_SUBCONFIG2" in [conf.get('name') for conf in confs])

    def test_pv_of_name_with_special_chars(self):
        CONFIG_NAME = "T#E'S@T_C[O]N{F}I^G$1"
        self._test_pv_changed_but_not_name(CONFIG_NAME, "TEST_CONFIG1")

    def test_pv_of_lower_case_name(self):
        CONFIG_NAME = "test_CONfig1"
        self._test_pv_changed_but_not_name(CONFIG_NAME, "TEST_CONFIG1")

    def test_pv_of_name_with_spaces(self):
        CONFIG_NAME = "TEST CONFIG1"
        self._test_pv_changed_but_not_name(CONFIG_NAME, "TEST_CONFIG1")

    def test_pv_of_name_with_no_alphanumeric_chars(self):
        CONFIG_NAME = "#'@&[]{}^$"
        self._test_pv_changed_but_not_name(CONFIG_NAME, "CONFIG")

    def test_pv_of_name_with_no_alpha_chars(self):
        CONFIG_NAME = "1 2_3 4"
        self._test_pv_changed_but_not_name(CONFIG_NAME, "CONFIG")

    def test_config_pv_of_repeated_name(self):
        create_configs(["TEST CONFIG", "TEST_CONFIG", "TEST_CO!NFIG", "TEST_CONFIG1"])
        ic = self._create_ic()
        confs = ic.get_configs()

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_CONFIG" in pvs)
        self.assertTrue("TEST_CONFIG0" in pvs)
        self.assertTrue("TEST_CONFIG1" in pvs)
        self.assertTrue("TEST_CONFIG10" in pvs)

    def test_subconfig_pv_of_repeated_name(self):
        create_subconfigs(["TEST SUBCONFIG", "TEST_SUBCONFIG", "TEST_SUBCO!NFIG", "TEST_SUBCONFIG1"])
        ic = self._create_ic()
        confs = ic.get_subconfigs()

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_SUBCONFIG" in pvs)
        self.assertTrue("TEST_SUBCONFIG0" in pvs)
        self.assertTrue("TEST_SUBCONFIG1" in pvs)
        self.assertTrue("TEST_SUBCONFIG10" in pvs)

    def test_config_and_subconfig_allowed_same_pv(self):
        create_configs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        create_subconfigs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        ic = self._create_ic()

        confs = ic.get_configs()
        self.assertEqual(len(confs), 2)

        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG" in [m["pv"] for m in confs])
        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG0" in [m["pv"] for m in confs])

        subconfs = ic.get_subconfigs()
        self.assertEqual(len(subconfs), 2)

        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG" in [m["pv"] for m in subconfs])
        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG0" in [m["pv"] for m in subconfs])

    def _test_is_configuration_json(self, data, name):
        self.assertTrue("name" in data)
        self.assertEqual(data["name"], name)
        self.assertTrue("iocs" in data)
        self.assertTrue("blocks" in data)
        self.assertTrue("groups" in data)
        self.assertTrue("description" in data)
        self.assertFalse("pv" in data)

    def _test_pv_changed_but_not_name(self, config_name, expected_pv_name):
        ms = self.ms
        create_configs([config_name])
        ic = self._create_ic()
        confs = ic.get_configs()

        self.assertEqual(len(confs), 1)

        self.assertEqual(confs[0]["pv"], expected_pv_name)
        self.assertEqual(confs[0]["name"], config_name)

        self.assertTrue(expected_pv_name + ":" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertFalse(config_name + ":" + GET_CONFIG_PV in ms.pv_list.keys())
        data = ms.pv_list.get(expected_pv_name + ":" + GET_CONFIG_PV)
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, config_name)

    def test_delete_configs_empty(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = self.ms
        ic = self._create_ic()

        ic.active_config_name = "TEST_ACTIVE"
        ic.delete_configs([])

        config_names = [c["name"] for c in ic.get_configs()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertEqual(len(ms.pv_list), 3)

    def test_delete_subconfigs_empty(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = self.ms
        ic = self._create_ic()

        ic.active_config_name = "TEST_ACTIVE"
        ic.delete_configs([], True)

        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_SUBCONFIG1" in config_names)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)

        self.assertEqual(len(ms.pv_list), 5)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_active_config(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = self.ms
        ic = self._create_ic()
        active = ActiveConfigHolder(CONFIG_PATH, MACROS, None, "archive.xml", MockVersionControl(), MockIocControl(""),
                                    test_mode=True)
        active.save_active("TEST_ACTIVE")
        ic.update_a_config_in_list(active)
        ic.active_config_name = "TEST_ACTIVE"

        self._test_none_deleted(ic, ms)
        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_ACTIVE"])
        self._test_none_deleted(ic, ms)
        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_ACTIVE", "TEST_CONFIG1"])
        self._test_none_deleted(ic, ms)
        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_CONFIG1", "TEST_ACTIVE"])
        self._test_none_deleted(ic, ms)

    def test_delete_active_subconfig(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = self.ms
        ic = self._create_ic()
        active = ActiveConfigHolder(CONFIG_PATH, MACROS, None, "archive.xml", MockVersionControl(), MockIocControl(""),
                                    test_mode=True)
        active.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        active.save_active("TEST_ACTIVE")
        ic.active_config_name = "TEST_ACTIVE"

        ic.update_a_config_in_list(active)

        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_SUBCONFIG1"], True)
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs,
                          ["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"], True)
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs,
                          ["TEST_CONFIG2", "TEST_SUBCONFIG1"], True)
        self._test_none_deleted(ic, ms, True)

    def test_delete_used_subconfig(self):
        sub1 = create_subconfigs(["TEST_SUBCONFIG3", "TEST_SUBCONFIG2", "TEST_SUBCONFIG1"])
        ms = self.ms
        ic = self._create_ic()

        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        inactive.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")

        ic.update_a_config_in_list(sub1, True)
        ic.update_a_config_in_list(inactive)
        ic.active_config_name = "TEST_ACTIVE"

        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_SUBCONFIG1"], True)
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs,
                          ["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"], True)
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(InvalidDeleteException, ic.delete_configs,
                          ["TEST_CONFIG2", "TEST_SUBCONFIG1"], True)
        self._test_none_deleted(ic, ms, True)

    def _test_none_deleted(self, ic, ms, is_subconfig=False):
        if is_subconfig:
            config_names = [c["name"] for c in ic.get_subconfigs()]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_SUBCONFIG1" in config_names)
            self.assertTrue("TEST_SUBCONFIG2" in config_names)
            self.assertTrue("TEST_SUBCONFIG3" in config_names)
        else:
            config_names = [c["name"] for c in ic.get_configs()]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_CONFIG2" in config_names)
            self.assertTrue("TEST_CONFIG1" in config_names)
            self.assertTrue("TEST_ACTIVE" in config_names)

    def test_delete_one_config(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = self.ms
        ic = self._create_ic()

        ic.delete_configs(["TEST_CONFIG1"])
        ic.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in ic.get_configs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)
        self.assertEqual(len(ms.pv_list), 2)

    def test_delete_one_subconfig(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = self.ms
        ic = self._create_ic()

        ic.delete_configs(["TEST_SUBCONFIG1"], True)
        ic.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)
        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_many_configs(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2", "TEST_CONFIG3"])
        ms = self.ms
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in ic.get_configs()]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertTrue("TEST_CONFIG3" in config_names)

        ic.delete_configs(["TEST_CONFIG1", "TEST_CONFIG3"])

        config_names = [c["name"] for c in ic.get_configs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)
        self.assertFalse("TEST_CONFIG3" in config_names)
        self.assertEqual(len(ms.pv_list), 2)

    def test_delete_many_subconfigs(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = self.ms
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_SUBCONFIG1" in config_names)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertTrue("TEST_SUBCONFIG3" in config_names)

        ic.delete_configs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG3"],  True)

        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)
        self.assertFalse("TEST_SUBCONFIG3" in config_names)
        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_config_affects_filesystem(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        self.assertEqual(len(os.listdir(CONFIG_PATH + CONFIG_DIRECTORY)), 2)
        ic.delete_configs(["TEST_CONFIG1"])

        configs = os.listdir(CONFIG_PATH + CONFIG_DIRECTORY)
        self.assertEqual(len(configs), 1)
        self.assertTrue("TEST_CONFIG2" in configs)

    def test_delete_subconfig_affects_filesystem(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        self.assertEqual(len(os.listdir(CONFIG_PATH + COMPONENT_DIRECTORY)), 3)
        ic.delete_configs(["TEST_SUBCONFIG1"], True)

        configs = os.listdir(CONFIG_PATH + COMPONENT_DIRECTORY)
        self.assertEqual(len(configs), 2)
        self.assertTrue("TEST_SUBCONFIG2" in configs)

    def test_cant_delete_non_existant_config(self):
        ms = self.ms
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_CONFIG1"])

        config_names = [c["name"] for c in ic.get_configs()]
        self.assertEqual(len(config_names), 0)
        self.assertEqual(len(ms.pv_list), 1)

    def test_cant_delete_non_existant_subconfig(self):
        ms = self.ms
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        self.assertRaises(InvalidDeleteException, ic.delete_configs, ["TEST_SUBCONFIG1"], True)

        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 0)
        self.assertEqual(len(ms.pv_list), 1)

    def test_delete_subconfig_after_add_and_remove(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = self.ms
        ic = self._create_ic()
        ic.active_config_name = "TEST_ACTIVE"

        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)

        inactive.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")
        ic.update_a_config_in_list(inactive)

        inactive.remove_subconfig("TEST_SUBCONFIG1")
        inactive.save_inactive("TEST_INACTIVE")
        ic.update_a_config_in_list(inactive)

        ic.delete_configs(["TEST_SUBCONFIG1"], True)
        config_names = [c["name"] for c in ic.get_subconfigs()]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertTrue("TEST_SUBCONFIG3" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)

        self.assertEqual(len(ms.pv_list), 6)
        self.assertTrue("TEST_INACTIVE:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG3:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG3:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_dependencies_initialises(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = self.ms
        self._create_ic()

        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)

    def test_dependencies_updates_add(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = self.ms
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)

        inactive.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE")
        ic.update_a_config_in_list(inactive)

        self.assertEqual(len(ms.pv_list), 4)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_INACTIVE".lower() in confs)

    def test_dependencies_updates_remove(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = self.ms
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)

        inactive.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        ic.update_a_config_in_list(inactive)

        inactive.remove_subconfig("TEST_SUBCONFIG1")
        inactive.save_inactive("TEST_INACTIVE", False)
        ic.update_a_config_in_list(inactive)

        self.assertEqual(len(ms.pv_list), 4)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)
        self.assertFalse("TEST_INACTIVE".lower() in confs)

    def test_delete_config_deletes_dependency(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = self.ms
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        ic.active_config_name = "TEST_ACTIVE"
        inactive.add_subconfig("TEST_SUBCONFIG1", Configuration(MACROS))
        inactive.save_inactive("TEST_INACTIVE", False)
        ic.update_a_config_in_list(inactive)

        ic.delete_configs(["TEST_INACTIVE"])

        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)
        self.assertFalse("TEST_INACTIVE".lower() in confs)

    def test_cannot_delete_default(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = self.ms
        ic = self._create_ic()

        self.assertRaises(InvalidDeleteException, ic.delete_configs, [DEFAULT_COMPONENT], True)

    def test_update_inactive_config_from_filewatcher(self):
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        self.bs.set_config_list(ic)

        inactive.save_inactive("TEST_INACTIVE")
        ic.update_a_config_in_list_filewatcher(inactive)

        self.assertEqual(len(self.bs.get_comps()), 0)
        self.assertEqual(len(self.bs.get_confs()), 1)
        self.assertTrue("TEST_INACTIVE" in [x['name'] for x in self.bs.get_confs()])
        self.assertEqual(ic.get_active_changed(), 0)
        self.assertEqual(self.ms.pv_list[CONFIG_CHANGED_PV], 0)

    def test_update_inactive_config_from_filewatcher(self):
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        self.bs.set_config_list(ic)

        inactive.save_inactive("TEST_INACTIVE_COMP", True)
        ic.update_a_config_in_list_filewatcher(inactive, True)

        self.assertEqual(len(self.bs.get_comps()), 1)
        self.assertEqual(len(self.bs.get_confs()), 0)
        self.assertTrue("TEST_INACTIVE_COMP" in [x['name'] for x in self.bs.get_comps()])
        self.assertEqual(ic.get_active_changed(), 0)
        self.assertEqual(self.ms.pv_list[CONFIG_CHANGED_PV], 0)

    def test_update_active_config_from_filewatcher(self):
        ic = self._create_ic()
        active = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        active_config_name = "TEST_ACTIVE"

        self.bs.set_config_list(ic)
        ic.active_config_name = active_config_name

        active.save_inactive(active_config_name)
        ic.update_a_config_in_list_filewatcher(active)

        self.assertEqual(len(self.bs.get_comps()), 0)
        self.assertEqual(len(self.bs.get_confs()), 1)
        self.assertTrue("TEST_ACTIVE" in [x['name'] for x in self.bs.get_confs()])
        self.assertEqual(ic.get_active_changed(), 1)
        self.assertEqual(self.ms.pv_list[CONFIG_CHANGED_PV], 1)

    def test_update_active_subconfig_from_filewatcher(self):
        ic = self._create_ic()
        inactive = InactiveConfigHolder(CONFIG_PATH, MACROS, MockVersionControl(), test_mode=True)
        active_config_name = "TEST_ACTIVE"
        active_config_comp = "TEST_ACTIVE_COMP"

        self.bs.set_config_list(ic)
        ic.active_config_name = active_config_name
        ic.active_components = [active_config_comp]

        inactive.save_inactive(active_config_comp, True)
        ic.update_a_config_in_list_filewatcher(inactive, True)

        self.assertEqual(len(self.bs.get_comps()), 1)
        self.assertEqual(len(self.bs.get_confs()), 0)
        self.assertTrue("TEST_ACTIVE_COMP" in [x['name'] for x in self.bs.get_comps()])
        self.assertEqual(ic.get_active_changed(), 1)
        self.assertEqual(self.ms.pv_list[CONFIG_CHANGED_PV], 1)

    def test_default_filtered(self):
        ic = self._create_ic()
        ms = self.ms

        comps = ic.get_subconfigs()
        self.assertTrue(DEFAULT_COMPONENT not in comps)

        self.assertEqual(len(ms.pv_list.keys()), 1)