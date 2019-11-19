from __future__ import print_function, unicode_literals, division, absolute_import

import json
import unittest
import sys
import os

from hamcrest import *
from mock import patch, MagicMock, mock_open
from pdfrw import compress

from BlockServer import fileIO
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from RemoteIocServer.config_monitor import ConfigurationMonitor, REMOTE_IOC_CONFIG_NAME
from server_common.utilities import compress_and_hex

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


LOCAL_TEST_PREFIX = "UNITTEST:SOMEPREFIX:"
REMOTE_TEST_PREFIX = "UNITTEST2:SOMEOTHERPREFIX:"

EMPTY_COMPONENTS_XML = """<?xml version="1.0" ?>
<components xmlns="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:comp="http://epics.isis.rl.ac.uk/schema/components/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>
"""

EMPTY_GROUPS_XML = """<?xml version="1.0" ?>
<groups xmlns="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:grp="http://epics.isis.rl.ac.uk/schema/groups/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>
"""

EMPTY_BLOCKS_XML = """<?xml version="1.0" ?>
<blocks xmlns="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:blk="http://epics.isis.rl.ac.uk/schema/blocks/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>
"""

META_XML = u'<?xml version="1.0" ?>\n<meta>\n\t<description>Configuration for remote IOC</description>\n\t<synoptic/>\n\t<edits/>\n\t<isProtected>false</isProtected>\n</meta>\n'


class TestConfigMonitor(unittest.TestCase):

    @patch("RemoteIocServer.config_monitor.get_hostname_from_prefix")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_WHEN_start_monitoring_THEN_monitor_called(self, epicsmonitor, get_hostname_from_prefix_mock):
        get_hostname_from_prefix_mock.return_value = "server"
        mon = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        mon.set_remote_pv_prefix(REMOTE_TEST_PREFIX)

        epicsmonitor.assert_called_with("{}CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS".format(REMOTE_TEST_PREFIX))
        epicsmonitor.return_value.start.assert_called_once()

    @patch("RemoteIocServer.config_monitor.get_hostname_from_prefix")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_WHEN_remote_pv_prefix_changed_THEN_old_monitor_ended(self, epicsmonitor, get_hostname):
        get_hostname.return_value = "localhost"
        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        monitor.set_remote_pv_prefix(REMOTE_TEST_PREFIX)

        epicsmonitor.return_value.end.assert_not_called()
        monitor.set_remote_pv_prefix(REMOTE_TEST_PREFIX)
        epicsmonitor.return_value.end.assert_called_once()

    @patch("RemoteIocServer.config_monitor.get_hostname_from_prefix")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_WHEN_remote_pv_prefix_changed_THEN_new_monitor_created(self, epicsmonitor, get_hostname):
        get_hostname.return_value = "localhost"
        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        monitor.set_remote_pv_prefix(REMOTE_TEST_PREFIX)

        epicsmonitor.return_value.start.assert_called_once()
        monitor.set_remote_pv_prefix(REMOTE_TEST_PREFIX)
        self.assertEqual(epicsmonitor.return_value.start.call_count, 2)

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("RemoteIocServer.config_monitor.dehex_and_decompress", return_value="abc")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_WHEN_config_updated_called_with_valid_value_THEN_no_errors_logger_and_calls_write_config(
            self, epicsmonitor, dehex, print_and_log):

        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        write_new = MagicMock()
        monitor.write_new_config_as_xml = write_new
        monitor._config_updated([ord(a) for a in compress_and_hex(str(""))])

        write_new.assert_called_once()
        print_and_log.assert_not_called()

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("RemoteIocServer.config_monitor.dehex_and_decompress", side_effect=ValueError)
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_WHEN_config_updated_called_with_invalid_value_THEN_error_logged_and_no_call_to_write_config(
            self, epicsmonitor, dehex, print_and_log):

        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        write_new = MagicMock()
        monitor.write_new_config_as_xml = write_new
        monitor._config_updated([0])

        write_new.assert_not_called()
        print_and_log.assert_called()

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("__builtin__.open")
    @patch("BlockServer.fileIO.file_manager.os")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_GIVEN_config_dir_not_existent_WHEN_write_config_as_xml_THEN_config_dir_created(
            self, epicsmonitor, os_mock, open_mock, print_and_log):
        FILEPATH_MANAGER.initialise("test_dir", "", "")
        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)

        os_mock.path.isdir.return_value = False

        monitor.write_new_config_as_xml("{}")

        os_mock.makedirs.assert_called_once()

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("__builtin__.open")
    @patch("BlockServer.fileIO.file_manager.os")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_GIVEN_config_dir_exists_WHEN_write_config_as_xml_THEN_config_dir_not_recreated(
            self, epicsmonitor, os_mock, open_mock, print_and_log):

        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)

        os_mock.path.isdir.return_value = True

        monitor.write_new_config_as_xml("{}")

        os_mock.mkdir.assert_not_called()

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("__builtin__.open")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_GIVEN_write_ioc_xml_called_WHEN_no_iocs_from_blockserver_THEN_appropriate_empty_xml_created(
            self, epicsmonitor, mock_open, print_and_log):

        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        FILEPATH_MANAGER.initialise("test_dir", "", "")
        with patch.object(FILEPATH_MANAGER, 'get_config_path', return_value="test_dir"):
            monitor.write_new_config_as_xml("{}")

        mock_open.assert_any_call(os.path.join("test_dir", "iocs.xml"), "w")
        mock_open.return_value.__enter__.return_value.write.assert_any_call(
            """<?xml version="1.0" ?>\n<iocs xmlns="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:ioc="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"/>\n""")

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("__builtin__.open")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_GIVEN_write_ioc_xml_called_WHEN_iocs_from_blockserver_THEN_appropriate_xml_created(
            self, epicsmonitor, mock_open, print_and_log):

        FILEPATH_MANAGER.initialise("test_dir", "", "")
        with patch.object(FILEPATH_MANAGER, 'get_config_path', return_value="test_dir"):
            monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
            monitor.write_new_config_as_xml(json.dumps({
                "component_iocs": [
                    {"macros": [], "pvs": [], "name": "INSTETC_01", "autostart": True, "pvsets": [], "component": "_base",
                     "remotePvPrefix": LOCAL_TEST_PREFIX, "restart": True, "simlevel": "none"},
                    {"macros": [], "pvs": [], "name": "ISISDAE_01", "autostart": True, "pvsets": [], "component": "_base",
                     "remotePvPrefix": LOCAL_TEST_PREFIX, "restart": True, "simlevel": "none"},
                ]}))

        mock_open.assert_any_call(os.path.join("test_dir", "iocs.xml"), "w")
        mock_open.return_value.__enter__.return_value.write.assert_any_call(
            '<?xml version="1.0" ?>\n'
            '<iocs xmlns="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:ioc="http://epics.isis.rl.ac.uk/schema/iocs/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">\n'
            '\t<ioc autostart="true" name="INSTETC_01" remotePvPrefix="{pf}" restart="true" simlevel="none">\n'
            '\t\t<macros>\n'
            '\t\t\t<macro name="ACF_IH1" value="None"/>\n'
            '\t\t</macros>\n'
            '\t\t<pvs/>\n'
            '\t\t<pvsets/>\n'
            '\t</ioc>\n'
            '\t<ioc autostart="true" name="ISISDAE_01" remotePvPrefix="{pf}" restart="true" simlevel="none">\n'
            '\t\t<macros>\n'
            '\t\t\t<macro name="ACF_IH1" value="None"/>\n'
            '\t\t</macros>\n'
            '\t\t<pvs/>\n'
            '\t\t<pvsets/>\n'
            '\t</ioc>\n'
            '</iocs>\n'.format(pf=LOCAL_TEST_PREFIX))

    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    @patch("__builtin__.open")
    @patch("RemoteIocServer.config_monitor.print_and_log")
    def test_GIVEN_write_standard_config_files_called_THEN_standard_config_files_written(
            self, epicsmonitor, mock_open, print_and_log):

        FILEPATH_MANAGER.initialise("test_dir", "", "")
        with patch.object(FILEPATH_MANAGER, 'get_config_path', return_value="test_dir"),\
                patch.object(fileIO.file_manager.os.path, 'isdir', return_value=True):
            monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
            monitor.write_new_config_as_xml("{}")

            all_writes = [args[0][0] for args in mock_open.return_value.__enter__.return_value.write.call_args_list]
            mock_open.assert_any_call(os.path.join("test_dir", "groups.xml"), "w")
            assert_that(all_writes, has_item(EMPTY_GROUPS_XML))

            mock_open.assert_any_call(os.path.join("test_dir", "components.xml"), "w")
            assert_that(all_writes, has_item(EMPTY_COMPONENTS_XML))

            mock_open.assert_any_call(os.path.join("test_dir", "blocks.xml"), "w")
            assert_that(all_writes, has_item(EMPTY_BLOCKS_XML))

            mock_open.assert_any_call(os.path.join("test_dir", "meta.xml"), "w")
            assert_that(all_writes, has_item(META_XML))

    @patch("RemoteIocServer.config_monitor.print_and_log")
    @patch("__builtin__.open")
    @patch("RemoteIocServer.config_monitor._EpicsMonitor")
    def test_GIVEN_update_last_config_called_THEN_standard_config_files_written(
            self, epicsmonitor, mock_open, print_and_log):

        monitor = ConfigurationMonitor(LOCAL_TEST_PREFIX, lambda *a, **k: None)
        FILEPATH_MANAGER.initialise("test_dir", "", "")
        expected_path = "last_config.txt"
        with patch.object(FILEPATH_MANAGER, 'get_last_config_file_path', return_value=expected_path):
            monitor.write_new_config_as_xml("{}")

            mock_open.assert_called_with(expected_path, "w")
            mock_open.return_value.__enter__.return_value.write.assert_called_with("{}\n".format(REMOTE_IOC_CONFIG_NAME))
