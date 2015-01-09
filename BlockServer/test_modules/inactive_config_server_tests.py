from all_configs_list import InactiveConfigListManager
from active_config_server import ActiveConfigServerManager
from mocks.mock_ca_server import MockCAServer
from server_common.utilities import dehex_and_decompress
import unittest
import json
import os
import shutil
from config_server import ConfigServerManager

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

TEST_DIRECTORY = "./test_configs"

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
        configserver = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                                test_mode=True)
        for name in names:
            configserver.save_config(json.dumps(name))

def create_subconfigs(names):
        configserver = ActiveConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                                test_mode=True)
        for name in names:
            configserver.save_as_subconfig(json.dumps(name))

class TestInactiveConfigsSequence(unittest.TestCase):

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(TEST_DIRECTORY)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_initialisation_with_no_configs_in_directory(self):
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer())
        confs = ic.get_config_names()
        self.assertEqual(len(confs), 0)
        subconfs = ic.get_subconfig_names()
        self.assertEqual(len(subconfs), 0)

    def test_initialisation_with_configs_in_directory(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer())
        confs = ic.get_config_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in confs)
        self.assertTrue("TEST_CONFIG2" in confs)

    def test_initialisation_with_subconfigs_in_directory(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY,MockCAServer())
        confs = ic.get_subconfig_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_SUBCONFIG1" in confs)
        self.assertTrue("TEST_SUBCONFIG2" in confs)

    def test_initialisation_with_configs_in_directory_pv(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_CONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertTrue("TEST_CONFIG2:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG2:GET_COMPONENT_DETAILS" in ms.pv_list.keys())

    def test_initialisation_with_subconfigs_in_directory_pv(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG2:GET_CONFIG_DETAILS" in ms.pv_list.keys())

    def test_initialisation_pv_config_data(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)
        data = ms.pv_list.get("TEST_CONFIG1:GET_CONFIG_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self.assertTrue("name" in data)
        self.assertEqual(data["name"], "TEST_CONFIG1")
        self._test_is_configuration_json(data, "TEST_CONFIG1")

    def test_initialisation_pv_config_data(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)
        data = ms.pv_list.get("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_SUBCONFIG1")

    def test_update_config_from_object(self):
        ics = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer())
        ic = ConfigServerManager(TEST_DIRECTORY, MACROS)
        ic.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))
        ics.update_config_list(ic)

        confs = json.loads(ics.get_configs_json())
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = json.loads(ics.get_subconfigs_json())
        self.assertEqual(len(subconfs), 0)

    def test_update_subconfig_from_object(self):
        ics = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer())
        ic = ConfigServerManager(TEST_DIRECTORY, MACROS)
        ic.set_config_details(strip_out_whitespace(VALID_CONFIG_JSON))
        ics.update_config_list(ic, True)

        confs = json.loads(ics.get_subconfigs_json())
        self.assertEqual(len(confs), 1)
        self.assertTrue("TEST_CONFIG" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG" in [conf.get('pv') for conf in confs])
        self.assertTrue("A Test Configuration" in [conf.get('description') for conf in confs])

        subconfs = json.loads(ics.get_configs_json())
        self.assertEqual(len(subconfs), 0)

    def test_subconfigs_json(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigListManager(TEST_DIRECTORY, MockCAServer())
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
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)
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
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)
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
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)

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
        ic = InactiveConfigListManager(TEST_DIRECTORY, ms)
        confs = json.loads(ic.get_configs_json())

        self.assertEqual(len(confs), 1)

        self.assertEqual(confs[0]["pv"], expected_pv_name)
        self.assertEqual(confs[0]["name"], config_name)

        self.assertTrue(expected_pv_name + ":GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse(config_name + ":GET_CONFIG_DETAILS" in ms.pv_list.keys())
        data = ms.pv_list.get(expected_pv_name + ":GET_CONFIG_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, config_name)