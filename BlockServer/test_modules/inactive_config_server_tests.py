__author__ = 'ffv81422'
from inactive_configs import InactiveConfigManager
from config_server import ConfigServerManager
from mocks.mock_ca_server import MockCAServer
from server_common.utilities import dehex_and_decompress
import unittest
import json
import os
import shutil

MACROS = {
    "$(MYPVPREFIX)": "",
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

TEST_DIRECTORY = "./test_configs"

def create_configs(names):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                                test_mode=True)
        for name in names:
            configserver.save_config(json.dumps(name))

def create_subconfigs(names):
        configserver = ConfigServerManager(TEST_DIRECTORY, MACROS, None, "archive.xml", "BLOCK_PREFIX:",
                                                test_mode=True)
        for name in names:
            configserver.save_as_subconfig(json.dumps(name))

class TestInactiveConfigsSequence(unittest.TestCase):

    def tearDown(self):
        # Delete any configs created as part of the test
        path = os.path.abspath(TEST_DIRECTORY)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def test_initialisation_no_configs(self):
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, MockCAServer())
        confs = ic.get_config_names()
        self.assertEqual(len(confs), 0)
        subconfs = ic.get_subconfig_names()
        self.assertEqual(len(subconfs), 0)

    def test_initialisation_configs(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, MockCAServer())
        confs = ic.get_config_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_CONFIG1" in confs)
        self.assertTrue("TEST_CONFIG2" in confs)

    def test_initialisation_subconfigs(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, MockCAServer())
        confs = ic.get_subconfig_names()
        self.assertEqual(len(confs), 2)
        self.assertTrue("TEST_SUBCONFIG1" in confs)
        self.assertTrue("TEST_SUBCONFIG2" in confs)

    def test_initialisation_config_pv(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_CONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertTrue("TEST_CONFIG2:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG2:GET_COMPONENT_DETAILS" in ms.pv_list.keys())

    def test_initialisation_subconfig_pv(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)

        self.assertEqual(len(ms.pv_list), 2)
        self.assertTrue("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertTrue("TEST_SUBCONFIG2:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG2:GET_CONFIG_DETAILS" in ms.pv_list.keys())

    def test_initialisation_pv_config_data(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        data = ms.pv_list.get("TEST_CONFIG1:GET_CONFIG_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self.assertTrue("name" in data)
        self.assertEqual(data["name"], "TEST_CONFIG1")
        self._test_is_configuration_json(data, "TEST_CONFIG1")

    def test_initialisation_pv_config_data(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        data = ms.pv_list.get("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_SUBCONFIG1")

    def test_update_config_from_file(self):
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])

        confs = json.loads(ic.get_configs_json())
        self.assertEqual(len(confs), 0)

        ic.update_config_from_file("TEST_CONFIG1")

        confs = json.loads(ic.get_configs_json())
        self.assertEqual(len(confs), 1)

        self.assertTrue("TEST_CONFIG1" in [conf.get('name') for conf in confs])
        self.assertFalse("TEST_CONFIG2" in [conf.get('name') for conf in confs])

        self.assertTrue("TEST_CONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_CONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())

        data = ms.pv_list.get("TEST_CONFIG1:GET_CONFIG_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_CONFIG1")

    def test_update_subconfig_from_file(self):
        ms = MockCAServer()
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])

        confs = json.loads(ic.get_subconfigs_json())
        self.assertEqual(len(confs), 0)

        ic.update_comp_from_file("TEST_SUBCONFIG1")

        confs = json.loads(ic.get_subconfigs_json())
        self.assertEqual(len(confs), 1)

        self.assertTrue("TEST_SUBCONFIG1" in [conf.get('name') for conf in confs])
        self.assertFalse("TEST_SUBCONFIG2" in [conf.get('name') for conf in confs])

        self.assertTrue("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS" in ms.pv_list.keys())
        self.assertFalse("TEST_SUBCONFIG1:GET_CONFIG_DETAILS" in ms.pv_list.keys())

        data = ms.pv_list.get("TEST_SUBCONFIG1:GET_COMPONENT_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, "TEST_SUBCONFIG1")

    def test_update_config_from_json(self):
        pass
        #TODO: this

    def test_update_subconfig_from_json(self):
        pass
        #TODO: this

    def test_configs_json(self):
        create_configs(["TEST_CONFIG1", "TEST_CONFIG2"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, MockCAServer())
        confs = json.loads(ic.get_configs_json())
        for conf in confs:
            self.assertEqual(len(conf), 3)
            self.assertTrue("name" in conf)
            self.assertTrue("pv" in conf)
            self.assertTrue("description" in conf)
        self.assertTrue("TEST_CONFIG1" in [conf.get('name') for conf in confs])
        self.assertTrue("TEST_CONFIG2" in [conf.get('name') for conf in confs])

    def test_subconfigs_json(self):
        create_subconfigs(["TEST_SUBCONFIG1", "TEST_SUBCONFIG2"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, MockCAServer())
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
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        confs = json.loads(ic.get_configs_json())

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        print pvs
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_CONFIG" in pvs)
        self.assertTrue("TEST_CONFIG0" in pvs)
        self.assertTrue("TEST_CONFIG1" in pvs)
        self.assertTrue("TEST_CONFIG10" in pvs)

    def test_subconfig_pv_of_repeated_name(self):
        ms = MockCAServer()
        create_subconfigs(["TEST SUBCONFIG", "TEST_SUBCONFIG", "TEST_SUBCO!NFIG", "TEST_SUBCONFIG1"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        confs = json.loads(ic.get_subconfigs_json())

        self.assertEqual(len(confs), 4)

        # Test PVs are unique
        pvs = [m["pv"] for m in confs]
        print pvs
        self.assertEqual(len(pvs), len(set(pvs)))

        self.assertTrue("TEST_SUBCONFIG" in pvs)
        self.assertTrue("TEST_SUBCONFIG0" in pvs)
        self.assertTrue("TEST_SUBCONFIG1" in pvs)
        self.assertTrue("TEST_SUBCONFIG10" in pvs)

    def test_config_and_subconfig_allowed_same_pv(self):
        ms = MockCAServer()
        create_configs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        create_subconfigs(["TEST CONFIG AND SUBCONFIG", "TEST_CONFIG_AND_SUBCONFIG"])
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)

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
        ic = InactiveConfigManager(TEST_DIRECTORY, MACROS, ms)
        confs = json.loads(ic.get_configs_json())

        self.assertEqual(len(confs), 1)

        self.assertEqual(confs[0]["pv"], expected_pv_name)
        self.assertEqual(confs[0]["name"], config_name)

        self.assertTrue(expected_pv_name + ":GET_CONFIG_DETAILS" in ms.pv_list.keys())
        self.assertFalse(config_name + ":GET_CONFIG_DETAILS" in ms.pv_list.keys())
        data = ms.pv_list.get(expected_pv_name + ":GET_CONFIG_DETAILS")
        data = json.loads(dehex_and_decompress(data))

        self._test_is_configuration_json(data, config_name)