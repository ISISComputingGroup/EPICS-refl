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
from mock import Mock

from BlockServer.config.block import Block
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager
from BlockServer.test_modules.helpers import modify_active
from BlockServer.core.constants import TAG_RC_SUSPEND_ON_INVALID, TAG_RC_ENABLE, TAG_RC_HIGH, TAG_RC_LOW

os.environ['MYPVPREFIX'] = ""

from BlockServer.runcontrol.runcontrol_manager import RunControlManager, RC_START_PV
from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.mocks.mock_channel_access import MockChannelAccess, PVS, ChannelAccessEnv
from BlockServer.mocks.mock_ioc_control import MockIocControl
import unittest
from datetime import datetime, timedelta
from mock import patch


MACROS = {
    "$(MYPVPREFIX)": os.environ['MYPVPREFIX']
}


# Helper methods
def quick_block_to_json(name, pv, group, local=True):
    return {'name': name, 'pv': pv, 'group': group, 'local': local}


def _get_relative_time(t, **kwargs):
    return datetime.strftime(t + timedelta(**kwargs), '%m/%d/%Y %H:%M:%S')


def _get_current_time():
    return datetime.strftime(datetime.now(), '%m/%d/%Y %H:%M:%S')


class TestRunControlSequence(unittest.TestCase):
    def setUp(self):
        self.cs = MockChannelAccess()
        self.set_start_time_of_run_control()
        self.mock_file_manager = MockConfigurationFileManager()
        self.active_config, self.ioc_control, self.run_control_manager, self.rcash = self._create_initial_runcontrol_manager()

    def _create_initial_runcontrol_manager(self):
        prefix = ""
        ioc_control = MockIocControl("")
        config_holder = ActiveConfigHolder(MACROS, None, self.mock_file_manager, ioc_control)
        run_control_autosave_helper = Mock()
        run_control_manager = RunControlManager(prefix, "", "", ioc_control, config_holder, MockBlockServer(), self.cs,
                                                run_control_auto_save_helper=run_control_autosave_helper)

        return config_holder, ioc_control, run_control_manager, run_control_autosave_helper

    def set_start_time_of_run_control(self, start_time=_get_current_time()):
        PVS[MACROS["$(MYPVPREFIX)"] + RC_START_PV] = start_time

    def test_get_runcontrol_settings_empty(self):
        self.set_start_time_of_run_control()
        self.run_control_manager.create_runcontrol_pvs(False, 0)
        ans = self.run_control_manager.get_current_settings()
        self.assertTrue(len(ans) == 0)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_get_runcontrol_settings_blocks(self, sleep_patch):
        self.active_config.add_block(quick_block_to_json("TESTBLOCK1", "PV1", "GROUP1", True))
        self.active_config.add_block(quick_block_to_json("TESTBLOCK2", "PV2", "GROUP2", True))
        self.active_config.add_block(quick_block_to_json("TESTBLOCK3", "PV3", "GROUP2", True))
        self.active_config.add_block(quick_block_to_json("TESTBLOCK4", "PV4", "NONE", True))
        self.set_start_time_of_run_control()
        self.run_control_manager.create_runcontrol_pvs(False, 0)
        ans = self.run_control_manager.get_current_settings()
        self.assertTrue(len(ans) == 4)
        for i in range(1, 5):
            block_name = "TESTBLOCK{}".format(i)
            self.assertTrue("HIGH" in ans[block_name])
            self.assertTrue("LOW" in ans[block_name])
            self.assertTrue("ENABLE" in ans[block_name])

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_get_runcontrol_settings_blocks_limits(self, sleep_patch):
        data = {'name': "TESTBLOCK1", 'pv': "PV1",
                'runcontrol': True, 'lowlimit': -5, 'highlimit': 5}
        self.active_config.add_block(data)
        self.set_start_time_of_run_control()
        self.run_control_manager.create_runcontrol_pvs(False, 0)
        ans = self.run_control_manager.get_current_settings()
        self.assertTrue(len(ans) == 1)
        self.assertTrue(ans["TESTBLOCK1"]["HIGH"] == 5)
        self.assertTrue(ans["TESTBLOCK1"]["LOW"] == -5)

    def test_GIVEN_non_restarting_runcontrol_WHEN_create_PVs_THAT_code_is_not_stuck_in_loop(self):
        rc_pv = RC_START_PV

        now = datetime.now()
        with ChannelAccessEnv({rc_pv: [_get_relative_time(now, minutes=-3)]}) as channel:
            self._create_initial_runcontrol_manager()
            self.assertEqual(channel.get_call_count(rc_pv), 1)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_GIVEN_already_started_runcontrol_WHEN_restart_THAT_code_is_not_stuck_in_loop(self, sleep_patch):
        rc_pv = RC_START_PV

        now = datetime.now()
        env = {rc_pv: [_get_relative_time(now, minutes=-3), "", _get_relative_time(now, minutes=-2)]}
        with ChannelAccessEnv(env) as channel:
            _, _, run_control_manager, _ = self._create_initial_runcontrol_manager()
            run_control_manager.create_runcontrol_pvs(True, 0)
            self.assertEqual(channel.get_call_count(rc_pv), 3)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_GIVEN_nonsense_runcontrol_start_time_WHEN_restart_runcontrol_THAT_code_loops_to_restart_runcontrol(self, sleep_patch):
        rc_pv = RC_START_PV
        with ChannelAccessEnv({rc_pv: [""] * 60}) as channel:
            self._create_initial_runcontrol_manager()
            self.assertEqual(channel.get_call_count(rc_pv), 60)

    def _modify_active(self, config_holder, new_details):
        modify_active("abc", MACROS, self.mock_file_manager, new_details, config_holder)

    def test_GIVEN_blocks_unchanged_and_not_full_init_WHEN_initialised_THEN_runcontrol_doesnt_restart_and_autosave_files_not_deleted(self):
        self._modify_active(self.active_config, self.active_config.get_block_details())

        self.run_control_manager.on_config_change(False)

        self.assertNotIn("RUNCTRL_01", self.ioc_control.restarted_iocs)
        self.assertFalse(self.rcash.clear_autosave_files.called)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_GIVEN_blocks_changed_and_not_full_init_WHEN_initialised_THEN_runcontrol_restarts_and_autosave_files_not_deleted(self, sleep_patch):
        config_details = self.active_config.get_config_details()
        config_details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(self.active_config, config_details)

        self.run_control_manager.on_config_change(False)

        self.assertIn("RUNCTRL_01", self.ioc_control.restarted_iocs)
        self.assertFalse(self.rcash.clear_autosave_files.called)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_GIVEN_blocks_unchanged_and_full_init_WHEN_initialised_THEN_runcontrol_restarts_and_autosave_files_deleted(self, sleep_patch):
        config_details = self.active_config.get_config_details()
        self._modify_active(self.active_config, config_details)

        self.run_control_manager.on_config_change(True)

        self.assertIn("RUNCTRL_01", self.ioc_control.restarted_iocs)
        self.assertTrue(self.rcash.clear_autosave_files.called)

    @patch("BlockServer.runcontrol.runcontrol_manager.sleep")
    def test_GIVEN_blocks_changed_and_full_init_WHEN_initialised_THEN_runcontrol_restarts_and_autosave_files_deleted(self, sleep_patch):
        config_details = self.active_config.get_config_details()
        config_details['blocks'].append(Block(name="TESTNAME", pv="TESTPV").to_dict())
        self._modify_active(self.active_config, config_details)

        self.run_control_manager.on_config_change(True)

        self.assertIn("RUNCTRL_01", self.ioc_control.restarted_iocs)
        self.assertTrue(self.rcash.clear_autosave_files.called)

    def test_GIVEN_enabled_block_WHEN_restore_config_settings_THEN_PVs_written_to(self):
        expected_low_limit, expected_high_limit = 10, 20
        blocks = {"my_block": Block("my_block", "my_pv", runcontrol=True,
                                    lowlimit=expected_low_limit, highlimit=expected_high_limit)}

        self.run_control_manager.restore_config_settings(blocks)
        rc_prefix = "CS:SB:my_block{}"
        self.assertEqual(expected_low_limit, self.cs.caget(rc_prefix.format(TAG_RC_LOW)))
        self.assertEqual(expected_high_limit, self.cs.caget(rc_prefix.format(TAG_RC_HIGH)))
        self.assertFalse(self.cs.caget(rc_prefix.format(TAG_RC_SUSPEND_ON_INVALID)))
        self.assertTrue(self.cs.caget(rc_prefix.format(TAG_RC_ENABLE)))

    def test_GIVEN_block_with_no_runcontrol_WHEN_restore_config_settings_THEN_runcontrol_disabled(self):
        blocks = {"my_block": Block("my_block", "my_pv")}

        self.run_control_manager.restore_config_settings(blocks)
        rc_prefix = "CS:SB:my_block{}"
        self.assertFalse(self.cs.caget(rc_prefix.format(TAG_RC_ENABLE)))
        self.assertFalse(self.cs.caget(rc_prefix.format(TAG_RC_SUSPEND_ON_INVALID)))
        self.assertFalse(rc_prefix.format(TAG_RC_LOW) in PVS)
        self.assertFalse(rc_prefix.format(TAG_RC_HIGH)in PVS)

    def test_GIVEN_multiple_blocks_WHEN_restore_config_settings_THEN_PVs_written_to(self):
        expected_low_limit, expected_high_limit = 30, 40
        blocks = dict()
        blocks["my_block"] = Block("my_block", "my_pv", runcontrol=True,
                                   lowlimit=expected_low_limit, highlimit=expected_high_limit)

        blocks["other_block"] = Block("other_block", "my_pv", runcontrol=False, suspend_on_invalid=True)

        self.run_control_manager.restore_config_settings(blocks)
        rc_prefix = "CS:SB:my_block{}"
        self.assertEqual(expected_low_limit, self.cs.caget(rc_prefix.format(TAG_RC_LOW)))
        self.assertEqual(expected_high_limit, self.cs.caget(rc_prefix.format(TAG_RC_HIGH)))
        self.assertTrue(self.cs.caget(rc_prefix.format(TAG_RC_ENABLE)))
        self.assertFalse(self.cs.caget(rc_prefix.format(TAG_RC_SUSPEND_ON_INVALID)))

        rc_prefix = "CS:SB:other_block{}"
        self.assertFalse(rc_prefix.format(TAG_RC_LOW) in PVS)
        self.assertFalse(rc_prefix.format(TAG_RC_HIGH)in PVS)
        self.assertTrue(self.cs.caget(rc_prefix.format(TAG_RC_SUSPEND_ON_INVALID)))
        self.assertFalse(self.cs.caget(rc_prefix.format(TAG_RC_ENABLE)))