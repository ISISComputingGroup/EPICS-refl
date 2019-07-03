import os
import unittest

from mock import patch

from RemoteIocServer.gateway import GateWay


TEST_LOCAL_PV_PREFIX = "LOCALINST:BLAH:"
TEST_REMOTE_PV_PREFIX = "REMOTEINST:BLAH:"


class GatewayTests(unittest.TestCase):

    @patch("RemoteIocServer.gateway.GateWay._reapply_gateway_settings")
    @patch("RemoteIocServer.gateway.print_and_log")
    def test_GIVEN_gateway_has_no_iocs_configured_WHEN_call_generate_gateway_file_THEN_get_empty_gateway_file(self, *_):
        gateway = GateWay(local_pv_prefix=TEST_LOCAL_PV_PREFIX,
                          gateway_restart_script_path="cmd.exe /c exit /b 0",
                          gateway_pvlist_file_path=os.devnull,
                          gateway_acf_path=os.devnull)

        gateway.set_remote_pv_prefix(TEST_REMOTE_PV_PREFIX)
        gateway.set_ioc_list([])
        alias_file_lines = gateway._get_alias_file_lines()
        self.assertEqual([], alias_file_lines)

    @patch("RemoteIocServer.gateway.GateWay._reapply_gateway_settings")
    @patch("RemoteIocServer.gateway.print_and_log")
    def test_GIVEN_gateway_has_iocs_configured_WHEN_call_generate_gateway_file_THEN_get_appropriate_lines(self, *_):
        gateway = GateWay(local_pv_prefix=TEST_LOCAL_PV_PREFIX,
                          gateway_restart_script_path="cmd.exe /c exit /b 0",
                          gateway_pvlist_file_path=os.devnull,
                          gateway_acf_path=os.devnull)

        gateway.set_remote_pv_prefix(TEST_REMOTE_PV_PREFIX)
        gateway.set_ioc_list(["DEVICE1", "DEVICE2"])
        alias_file_lines = gateway._get_alias_file_lines()
        self.assertEqual([
            'REMOTEINST:BLAH:DEVICE1:\\(.*\\)    ALIAS    LOCALINST:BLAH:DEVICE1:\\1',
            'REMOTEINST:BLAH:DEVICE2:\\(.*\\)    ALIAS    LOCALINST:BLAH:DEVICE2:\\1'
        ], alias_file_lines)
