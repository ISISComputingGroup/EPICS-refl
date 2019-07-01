import os
import unittest

from mock import patch

from RemoteIocServer.gateway import GateWay


TEST_PV_PREFIX = "UNITTEST:BLAH:"
TEST_INSTRUMENT = "UNITTESTINST"


class GatewayTests(unittest.TestCase):

    @patch("RemoteIocServer.gateway.print_and_log")
    def test_GIVEN_gateway_has_no_iocs_configured_WHEN_call_generate_gateway_file_THEN_get_empty_gateway_file(self, *_):
        gateway = GateWay(local_pv_prefix=TEST_PV_PREFIX,
                          gateway_restart_script_path="cmd.exe /c exit /b 0",
                          gateway_settings_file_path=os.devnull)

        gateway.set_remote_pv_prefix(TEST_INSTRUMENT)
        gateway.set_ioc_list([])
        alias_file_lines = gateway._get_alias_file_lines()
        self.assertEqual([], alias_file_lines)

    @patch("RemoteIocServer.gateway.print_and_log")
    def test_GIVEN_gateway_has_iocs_configured_WHEN_call_generate_gateway_file_THEN_get_appropriate_lines(self, *_):
        gateway = GateWay(local_pv_prefix=TEST_PV_PREFIX,
                          gateway_restart_script_path="cmd.exe /c exit /b 0",
                          gateway_settings_file_path=os.devnull)

        gateway.set_remote_pv_prefix(TEST_INSTRUMENT)
        gateway.set_ioc_list(["DEVICE1", "DEVICE2"])
        alias_file_lines = gateway._get_alias_file_lines()
        self.assertEqual([
            'ME:UNITTESTINST:DEVICE1:\\(.*\\)    ALIAS    UNITTEST:BLAH:DEVICE1:\\1',
            'ME:UNITTESTINST:DEVICE2:\\(.*\\)    ALIAS    UNITTEST:BLAH:DEVICE2:\\1'
        ], alias_file_lines)
