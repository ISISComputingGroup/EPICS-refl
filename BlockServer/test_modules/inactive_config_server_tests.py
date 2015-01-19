from all_configs_list import InactiveConfigListManager
from active_config_server import ActiveConfigServerManager
from server_common.mocks.mock_ca_server import MockCAServer
from server_common.utilities import dehex_and_decompress
import unittest
import json
import os
import shutil
from config_server import ConfigServerManager
from config.constants import COMPONENT_DIRECTORY, CONFIG_DIRECTORY

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

TEST_DIRECTORY = "./test_configs"

GET_CONFIG_PV = "GET_CONFIG_DETAILS"
GET_SUBCONFIG_PV = "GET_COMPONENT_DETAILS"
DEPENDENCIES_PV = "DEPENDENCIES"

VALID_CONFIG_JSON = u"""{
        "iocs": [{
            "simlevel": "None",
            "autostart": true,
            "restart": false,
            "pvsets": [{"name": "SET", "value": "true"}],
            "pvs": [{"name": "A_PV", "value": "TEST"}],
            "macros": [{"name": "A_MACRO", "value": "TEST"}],
            "name": "AN_IOC",
            "subconfig": null}],
        "blocks": [{
            "name": "TEST_BLOCK",
            "local": true,
            "pv": "NDWXXX:xxxx:TESTPV",
            "subconfig": null,
            "visible": true}],
        "components": [],
        "groups": [{
            "blocks": ["TEST_BLOCK"], "name": "TEST_GROUP", "subconfig": null}],
        "name": "TEST_CONFIG",
        "description": "A Test Configuration"}"""

def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "").replace("\n", "")

def create_configs(names):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        for name in names:
            configserver.save_config(json.dumps(name))

def create_subconfigs(names):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        for name in names:
            configserver.save_as_subconfig(json.dumps(name))

        return configserver

class TestInactiveConfigsSequence(unittest.TestCase):

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(TEST_DIRECTORY)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_initialisation_with_no_configs_in_directory(self):
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer(), test_mode=True)
        confs = ic._get_config_names()
        self.assertEqual(len(confs), 0)
        subconfs = ic._get_subconfig_names()
        self.assertEqual(len(subconfs), 0)

    def test_initialisation_with_configs_in_directory(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer(), test_mode=True)
        confs = ic._get_config_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in confs)
        self.assertTrue("TEST_CONFIG2" in confs)

    def test_initialisation_with_subconfigs_in_directory(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY,MockCAServer(), test_mode=True)
        confs = ic._get_subconfig_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_SUBCONFIG1" in confs)
        self.assertTrue("TEST_SUBCONFIG2" in confs)

    def test_initialisation_with_configs_in_directory_pv(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_CONFIG1:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_CONFIG2:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())

    def test_initialisation_with_subconfigs_in_directory_pv(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)

        self.assertEqual(len(ms.pv_list), 4)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG1:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG2:" + GET_CONFIG_PV in ms.pv_list.keys())

    def test_initialisation_pv_config_data(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        data = ms.pv_list.get("TEST_CONFIG1:" + GET_CONFIG_PV)
        data = json.loads(dehex_and_decompress(data))

        self.assertTrue("name" in data)
        self.assertEqual(data["name"], "TEST_CONFIG1")
        self._test_is_configuration_json(data, "TEST_CONFIG1")

    def test_initialisation_pv_config_data(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        data = ms.pv_list.get("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV)
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_SUBCONFIG1")

    def test_update_config_from_object(self):
        ics = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer(), test_mode=True)
        ic = ConfigServerManager(TEST_DIRECTORY, MACROS)
        ic.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))
        ics.update_a_config_in_list(ic)

        confs = json.loads(ics.get_configs_json())
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = json.loads(ics.get_subconfigs_json())
        self.assertEqual(len(subconfs), 0)

    def test_update_subconfig_from_object(self):
        ics = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer(), test_mode=True)
        ic = ConfigServerManager(TEST_DIRECTORY, MACROS)
        ic.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))
        ics.update_a_config_in_list(ic, True)

        confs = json.loads(ics.get_subconfigs_json())
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = json.loads(ics.get_configs_json())
        self.assertEqual(len(subconfs), 0)

    def test_subconfigs_json(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer(), test_mode=True)
        confs = json.loads(ic.get_subconfigs_json())
        for conf in confs:
            self.assertEqual(len(conf), 3)
            self.assertTrue("name" in conf)
            self.assertTrue("pv" in conf)
            self.assertTrue("description" in conf)
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
        ms = MockCAServer()
        create_configs(["TEST CONFIG", "TEST_CONFIG", "TEST_CO!NFIG", "TEST_CONFIG1"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        confs = json.loads(ic.get_configs_json())

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_CONFIG" in pvs)
        self.assertTrue("TEST_CONFIG0" in pvs)
        self.assertTrue("TEST_CONFIG1" in pvs)
        self.assertTrue("TEST_CONFIG10" in pvs)

    def test_subconfig_pv_of_repeated_name(self):
        ms = MockCAServer()
        create_subconfigs(["TEST SUBCONFIG", "TEST_SUBCONFIG", "TEST_SUBCO!NFIG", "TEST_SUBCONFIG1"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        confs = json.loads(ic.get_subconfigs_json())

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_SUBCONFIG" in pvs)
        self.assertTrue("TEST_SUBCONFIG0" in pvs)
        self.assertTrue("TEST_SUBCONFIG1" in pvs)
        self.assertTrue("TEST_SUBCONFIG10" in pvs)

    def test_config_and_subconfig_allowed_same_pv(self):
        ms = MockCAServer()
        create_configs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        create_subconfigs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)

        confs = json.loads(ic.get_configs_json())
        self.assertEqual(len(confs), 2)

        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG" in [m["pv"] for m in confs])
        self.assertTrue("TEST_CONFIG_AND_SUBCONFIG0" in [m["pv"] for m in confs])

        subconfs = json.loads(ic.get_subconfigs_json())
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
        ms = MockCAServer()
        create_configs([config_name])
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        confs = json.loads(ic.get_configs_json())

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
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        ic.delete_configs(json.dumps([]), active)

        config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertEqual(len(ms.pv_list), 2)

    def test_delete_subconfigs_empty(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        ic.delete_configs(json.dumps([]), active, True)

        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_SUBCONFIG1" in config_names)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)

        self.assertEqual(len(ms.pv_list), 4)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_active_config(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.save_config(json.dumps("TEST_ACTIVE"))

        self._test_none_deleted(ic, ms)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_ACTIVE"]), active))
        self._test_none_deleted(ic, ms)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_ACTIVE", "TEST_CONFIG1"]), active))
        self._test_none_deleted(ic, ms)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_CONFIG1", "TEST_ACTIVE"]), active))
        self._test_none_deleted(ic, ms)

    def test_delete_active_subconfig(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        active.save_config(json.dumps("TEST_ACTIVE"))

        ic.update_a_config_in_list(active)

        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_SUBCONFIG1"]), active, True))
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"]), active, True))
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_CONFIG2", "TEST_SUBCONFIG1"]), active, True))
        self._test_none_deleted(ic, ms, True)

    def test_delete_used_subconfig(self):
        sub1 = create_subconfigs(["TEST_SUBCONFIG3", "TEST_SUBCONFIG2", "TEST_SUBCONFIG1"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)

        inactive = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        inactive.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))

        ic.update_a_config_in_list(sub1, True)
        ic.update_a_config_in_list(inactive)

        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_SUBCONFIG1"]), active, True))
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"]), active, True))
        self._test_none_deleted(ic, ms, True)
        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_CONFIG2", "TEST_SUBCONFIG1"]), active, True))
        self._test_none_deleted(ic, ms, True)

    def _test_none_deleted(self, ic, ms, is_subconfig=False):
        if is_subconfig:
            config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_SUBCONFIG1" in config_names)
            self.assertTrue("TEST_SUBCONFIG2" in config_names)
            self.assertTrue("TEST_SUBCONFIG3" in config_names)
        else:
            config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
            self.assertEqual(len(config_names), 3)
            self.assertTrue("TEST_CONFIG2" in config_names)
            self.assertTrue("TEST_CONFIG1" in config_names)
            self.assertTrue("TEST_ACTIVE" in config_names)

    def test_delete_one_config(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        ic.delete_configs(json.dumps(["TEST_CONFIG1"]), active)

        config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)
        self.assertEqual(len(ms.pv_list), 1)

    def test_delete_one_subconfig(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        ic.delete_configs(json.dumps(["TEST_SUBCONFIG1"]), active, True)

        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)
        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_many_configs(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2", "TEST_CONFIG3"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_CONFIG1" in config_names)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertTrue("TEST_CONFIG3" in config_names)

        ic.delete_configs(json.dumps(["TEST_CONFIG1", "TEST_CONFIG3"]), active)

        config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_CONFIG2" in config_names)
        self.assertFalse("TEST_CONFIG1" in config_names)
        self.assertFalse("TEST_CONFIG3" in config_names)
        self.assertEqual(len(ms.pv_list), 1)

    def test_delete_many_subconfigs(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 3)
        self.assertTrue("TEST_SUBCONFIG1" in config_names)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertTrue("TEST_SUBCONFIG3" in config_names)

        ic.delete_configs(json.dumps(["TEST_SUBCONFIG1", "TEST_SUBCONFIG3"]), active, True)

        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 1)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)
        self.assertFalse("TEST_SUBCONFIG3" in config_names)
        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_delete_config_affects_filesystem(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        self.assertEqual(len(os.listdir(TEST_DIRECTORY + CONFIG_DIRECTORY)), 2)
        ic.delete_configs(json.dumps(["TEST_CONFIG1"]), active)

        configs = os.listdir(TEST_DIRECTORY + CONFIG_DIRECTORY)
        self.assertEqual(len(configs), 1)
        self.assertTrue("TEST_CONFIG2" in configs)

    def test_cant_delete_non_existant_config(self):
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_CONFIG1"]), active))

        config_names = [c["name"] for c in json.loads(ic.get_configs_json())]
        self.assertEqual(len(config_names), 0)
        self.assertEqual(len(ms.pv_list), 0)

    def test_cant_delete_non_existant_subconfig(self):
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)
        active.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))

        self.assertRaises(Exception, ic.delete_configs, (json.dumps(["TEST_SUBCONFIG1"]), active, True))

        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 0)
        self.assertEqual(len(ms.pv_list), 0)

    def test_delete_subconfig_after_add_and_remove(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2", "TEST_SUBCONFIG3"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)

        inactive = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)

        inactive.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        inactive.remove_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        ic.delete_configs(json.dumps(["TEST_SUBCONFIG1"]), active, True)
        config_names = [c["name"] for c in json.loads(ic.get_subconfigs_json())]
        self.assertEqual(len(config_names), 2)
        self.assertTrue("TEST_SUBCONFIG2" in config_names)
        self.assertTrue("TEST_SUBCONFIG3" in config_names)
        self.assertFalse("TEST_SUBCONFIG1" in config_names)

        self.assertEqual(len(ms.pv_list), 5)
        self.assertTrue("TEST_INACTIVE:" + GET_CONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:" + DEPENDENCIES_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG3:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG3:" + DEPENDENCIES_PV in ms.pv_list.keys())

    def test_dependencies_initialises(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)

    def test_dependencies_updates_add(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        inactive = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)

        inactive.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_INACTIVE".lower() in confs)

    def test_dependencies_updates_remove(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        inactive = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)

        inactive.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        inactive.remove_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        self.assertEqual(len(ms.pv_list), 3)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)
        self.assertFalse("TEST_INACTIVE".lower() in confs)

    def test_delete_config_deletes_dependency(self):
        create_subconfigs(["TEST_SUBCONFIG1"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms, test_mode=True)
        inactive = ConfigServerManager(TEST_DIRECTORY, MACROS, test_mode=True)
        active = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                            test_mode=True)

        inactive.add_subconfigs(json.dumps(["TEST_SUBCONFIG1"]))
        inactive.save_config(json.dumps("TEST_INACTIVE"))
        ic.update_a_config_in_list(inactive)

        ic.delete_configs(json.dumps(["TEST_INACTIVE"]), active)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG1:" + GET_SUBCONFIG_PV in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG1:" + DEPENDENCIES_PV in ms.pv_list.keys())

        confs = json.loads(dehex_and_decompress(ms.pv_list.get("TEST_SUBCONFIG1:" + DEPENDENCIES_PV)))
        self.assertEqual(len(confs), 0)
        self.assertFalse("TEST_INACTIVE".lower() in confs)

