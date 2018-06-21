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
import os

# Set MYPVPREFIX env var
from hamcrest import *
from mock import Mock

from ArchiverAccess.test_modules.stubs import FileStub
from BlockServer.config.block import Block
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager

os.environ['MYPVPREFIX'] = ""

from BlockServer.runcontrol.runcontrol_manager import RunControlManager, RC_START_PV
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_channel_access import MockChannelAccess, PVS, ChannelAccessEnv
from BlockServer.mocks.mock_active_config_holder import MockActiveConfigHolder
from BlockServer.config.configuration import Configuration
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.mocks.mock_ioc_control import MockIocControl
from BlockServer.mocks.mock_archiver_wrapper import MockArchiverWrapper
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
import unittest
from datetime import datetime, timedelta


HEADER_XML= """<?xml version="1.0" ?>
<engineconfig>
\t<group>
\t\t<name>BLOCKS</name>
"""

BLOCKS_TO_DATAWEB_XML="""\t</group>
\t<group>
\t\t<name>DATAWEB</name>
"""

FOOTER_XML="""\t</group>
</engineconfig>
"""

SCAN_BLOCK="""\t\t<channel>
\t\t\t<name>{prefix}{block_name}</name>
\t\t\t<period>0:{period_min:02}:{period_s:02}</period>
\t\t\t<scan/>
\t\t</channel>
"""

MONITOR_BLOCK="""\t\t<channel>
\t\t\t<name>{prefix}{block_name}</name>
\t\t\t<period>0:00:01</period>
\t\t\t<monitor>{deadband}</monitor>
\t\t</channel>
"""

class TestArchiveManager(unittest.TestCase):

    def setUp(self):
        self._setting_path = "blockserver_xml_path"
        self.archiver_manager = ArchiverManager(uploader_path=None, settings_path=self._setting_path, file_access_class=FileStub)
        FileStub.clear()

    def test_GIVEN_no_blocks_WHEN_update_THEN_xml_for_archiver_contains_just_header(self):
        blocks = []
        prefix = "prefix"
        expected_output = "{}{}{}".format(HEADER_XML, BLOCKS_TO_DATAWEB_XML, FOOTER_XML).splitlines()

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], contains(*expected_output))

    def test_GIVEN_one_blocks_is_not_logged_WHEN_update_THEN_xml_for_archiver_contains_block_in_dataweb_group(self):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name, period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    def test_GIVEN_one_blocks_is_logged_periodic_WHEN_update_THEN_xml_for_archiver_contains_periodic_block(self):
        expected_name="block"
        expected_pv = "pv"
        expecter_logging_rate_s = 30
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=expecter_logging_rate_s, log_deadband=1)]
        prefix = "prefix"
        block_str = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name, period_s=expecter_logging_rate_s, period_min=0)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    def test_GIVEN_one_blocks_is_not_periodic_WHEN_update_THEN_xml_for_archiver_contains_periodic_block(self):
        expected_name="block"
        expected_pv = "pv"
        expected_deadband = 30
        blocks = [Block(expected_name, expected_pv, log_periodic=False, log_rate=1, log_deadband=expected_deadband)]
        prefix = "prefix"
        block_str = MONITOR_BLOCK.format(prefix=prefix, block_name=expected_name, deadband=expected_deadband)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_low_value_block_in_dataweb_group(self):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":LOW.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_high_value_block_in_dataweb_group(self):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":HIGH.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_inrange_block_in_dataweb_group(self):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":INRANGE.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_enabled_block_in_dataweb_group(self):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":ENABLE.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks)

        assert_that(FileStub.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))