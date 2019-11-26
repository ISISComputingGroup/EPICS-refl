"""Run control manager."""
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.  This program
# and the accompanying materials are made available under the terms of the
# Eclipse Public License v1.0 which accompanies this distribution.  EXCEPT AS
# EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM AND
# ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more
# details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import os
from datetime import datetime
from time import sleep

import six
from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, \
    TAG_RC_ENABLE, TAG_RC_OUT_LIST, TAG_RC_SUSPEND_ON_INVALID
from BlockServer.core.on_the_fly_pv_interface import OnTheFlyPvInterface
from server_common.utilities import print_and_log, compress_and_hex, \
    convert_to_json, ioc_restart_pending
from server_common.channel_access import ChannelAccess
from server_common.pv_names import prepend_blockserver

TAG_RC_DICT = {
    "LOW": TAG_RC_LOW,
    "HIGH": TAG_RC_HIGH,
    "ENABLE": TAG_RC_ENABLE,
    "SUSPEND_ON_INVALID": TAG_RC_SUSPEND_ON_INVALID,
}

RC_IOC_PREFIX = "CS:PS:RUNCTRL_01"
RC_START_PV = "CS:IOC:RUNCTRL_01:DEVIOS:STARTTOD"
RUNCONTROL_SETTINGS = "rc_settings.cmd"
AUTOSAVE_DIR = "autosave"
RUNCONTROL_IOC = "RUNCTRL_01"

RUNCONTROL_OUT_PV = prepend_blockserver('GET_RC_OUT')
RUNCONTROL_GET_PV = prepend_blockserver('GET_RC_PARS')

# number of loops to wait for assuming the run control is not going to start
MAX_LOOPS_TO_WAIT_FOR_START = 60  # roughly 2 minutes at standard time


class _RunControlAutoSaveHelper(object):

    def __init__(self):
        self._autosave_dir = None

    def clear_autosave_files(self):
        for fname in os.listdir(self._autosave_dir):
            file_path = os.path.join(self._autosave_dir, fname)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as err:
                print_and_log("Problem deleting autosave files for the "
                              "run-control IOC: {}".format(str(err)), "MAJOR")

    def set_var_dir(self, var_dir):
        self._autosave_dir = os.path.join(var_dir, AUTOSAVE_DIR,
                                          RUNCONTROL_IOC)
        print_and_log("RUNCONTROL AUTOSAVE DIRECTORY: {}".format(self._autosave_dir))


class RunControlManager(OnTheFlyPvInterface):
    """A class for taking care of setting up run-control."""

    def __init__(self, prefix, config_dir, var_dir, ioc_control,
                 active_configholder, block_server,
                 channel_access=ChannelAccess(),
                 run_control_auto_save_helper=None):
        """
        Constructor.

        Args:
            prefix (string): The instrument prefix
            config_dir (string): The root of the configuration directory
            var_dir (string): The root of the VAR directory
            ioc_control (IocControl): The object for restarting the IOC
            active_configholder (ActiveConfigHolder): The current configuration
            block_server (BlockServer): A reference to the BlockServer instance
            channel_access (ChannelAccess): A reference to the ChannelAccess
                instance
            run_control_auto_save_helper (_RunControlAutoSaveHelper) : RunControlAutoSaveHelper
            instance, leave as None for normal operation.
        """
        self._rc_ioc_start_time = None
        self._prefix = prefix
        self._settings_file = os.path.join(config_dir, RUNCONTROL_SETTINGS)
        self._block_prefix = prefix + "CS:SB:"
        self._ioc_control = ioc_control
        self._active_configholder = active_configholder
        self._bs = block_server
        self._pvs_to_read = [RUNCONTROL_GET_PV, RUNCONTROL_OUT_PV]
        self._create_standard_pvs()
        self._channel_access = channel_access
        print_and_log("RUNCONTROL SETTINGS FILE: {}".format(self._settings_file))
        self._intialise_runcontrol_ioc()
        if run_control_auto_save_helper is None:
            self._run_control_auto_save_helper = _RunControlAutoSaveHelper()
        else:
            self._run_control_auto_save_helper = run_control_auto_save_helper
        self._run_control_auto_save_helper.set_var_dir(var_dir)

    def read_pv_exists(self, pv):
        """
        Check if a PV exists.
        """
        return pv in self._pvs_to_read

    def write_pv_exists(self, pv):
        """
        Unimplemented.
        """
        return False

    def handle_pv_write(self, pv, data):
        """
        Unimplemented.
        """
        # Nothing to write
        pass

    def handle_pv_read(self, pv):
        """
        Handle reading a run control PV.
        """
        if pv == RUNCONTROL_GET_PV:
            js = convert_to_json(self.get_current_settings())
            return compress_and_hex(js)
        elif pv == RUNCONTROL_OUT_PV:
            js = convert_to_json(self.get_out_of_range_pvs())
            return compress_and_hex(js)
        return ""

    def update_monitors(self):
        """
        Unimplemented.
        """
        # No monitors
        pass

    def on_config_change(self, full_init=False):
        """
        Initilise & create a new set of run control PVs.
        """
        self.create_runcontrol_pvs(full_init)

    def _create_standard_pvs(self):
        self._bs.add_string_pv_to_db(RUNCONTROL_OUT_PV, 16000)
        self._bs.add_string_pv_to_db(RUNCONTROL_GET_PV, 16000)

    def _intialise_runcontrol_ioc(self):
        # Start runcontrol IOC
        self._start_ioc()
        # Need to wait for RUNCONTROL_IOC to start
        self.wait_for_ioc_start()
        print_and_log("Runcontrol IOC started")

    def create_runcontrol_pvs(self, clear_autosave, time_between_tries=2):
        """
        Create the PVs for run-control.

        Configures the run-control IOC to have PVs for the current
        configuration.

        Args:
            clear_autosave: Whether to remove any values stored by autosave
            time_between_tries: Time to wait between checking run control has
                started
        """
        if self._active_configholder.blocks_changed() or clear_autosave:
            print_and_log("Start creating runcontrol PVs")
            self.update_runcontrol_blocks(
                self._active_configholder.get_block_details())
            self.restart_ioc(clear_autosave)
            # Need to wait for RUNCONTROL_IOC to restart
            self.wait_for_ioc_start(time_between_tries)
            print_and_log("Finish creating runcontrol PVs")

            print_and_log("Start arbitrary wait after creating runcontrol PVs")
            # If this sleep is not done, sometimes the config settings will not overwrite the current settings
            # correctly. See https://github.com/ISISComputingGroup/IBEX/issues/4344
            sleep(2)
            print_and_log("Finish arbitrary wait after creating runcontrol PVs")

            print_and_log("Restoring config settings...")
            self.restore_config_settings(
                self._active_configholder.get_block_details())
            print_and_log("Finish restoring config settings")

    def update_runcontrol_blocks(self, blocks):
        """
        Update the run-control settings in the IOC with the current blocks.

        Args:
            blocks (OrderedDict): The blocks that are part of the current
                configuration
        """
        try:
            with open(self._settings_file, 'w') as f:
                for bn, blk in six.iteritems(blocks):
                    f.write('dbLoadRecords("$(RUNCONTROL)/db/runcontrol.db",'
                            '"P=$(MYPVPREFIX),PV=$(MYPVPREFIX)CS:SB:%s")\n'
                            % blk.name)
                # Need an extra blank line
                f.write("\n")
        except Exception as err:
            print_and_log(str(err))

    def get_out_of_range_pvs(self):
        """
        Get a list of PVs that are currently out of range.

        This may include PVs that are not blocks, but have had run-control
        settings applied directly

        Returns:
            list : A list of PVs that are out of range

        """
        raw = self._channel_access.caget(self._prefix + TAG_RC_OUT_LIST, True).strip().split(" ")

        if raw is not None and len(raw) > 0:
            return [pv for pv in raw if len(pv) > 0]
        else:
            return []

    def get_current_settings(self):
        """
        Get the current run-control settings.

        Returns:
            dict : The current run-control settings

        """
        blocks = self._active_configholder.get_block_details()
        settings = dict()
        for bn, blk in six.iteritems(blocks):
            low = self._channel_access.caget(self._block_prefix
                                             + blk.name + TAG_RC_LOW)
            high = self._channel_access.caget(self._block_prefix +
                                              blk.name + TAG_RC_HIGH)
            enable = self._channel_access.caget(self._block_prefix +
                                                blk.name + TAG_RC_ENABLE, True)

            settings[blk.name] = {"LOW": low, "HIGH": high, "ENABLE": enable == "YES"}
        return settings

    def restore_config_settings(self, blocks):
        """
        Restore run-control settings based on what is stored in a configuration.

        Args:
            blocks (OrderedDict): The blocks for the configuration
        """
        for n, blk in six.iteritems(blocks):
            settings = dict()
            if blk.rc_enabled:
                settings["ENABLE"] = True
            else:
                settings["ENABLE"] = False
            if blk.rc_lowlimit is not None:
                settings["LOW"] = blk.rc_lowlimit
            if blk.rc_highlimit is not None:
                settings["HIGH"] = blk.rc_highlimit
            if blk.rc_suspend_on_invalid is not None:
                settings["SUSPEND_ON_INVALID"] = blk.rc_suspend_on_invalid
            self._set_rc_values(blk.name, settings)

    def _set_rc_values(self, block_name, settings):
        for key, value in six.iteritems(settings):
            if key.upper() in TAG_RC_DICT.keys():
                try:
                    self._channel_access.caput(self._block_prefix + block_name + TAG_RC_DICT[key.upper()], value)
                except Exception as err:
                    print_and_log("Problem with setting runcontrol for {}: {}".format(block_name, err))

    def _get_latest_ioc_start(self):
        """
        Get the latest IOC start time.

        Returns:
            latest_ioc_start (datetime): the latest IOC start time

        """
        raw_ioc_time = self._channel_access.caget(self._prefix + RC_START_PV)

        try:
            frmt = '%m/%d/%Y %H:%M:%S'
            latest_ioc_start = datetime.strptime(raw_ioc_time, frmt)
        except TypeError:
            latest_ioc_start = None
            print_and_log("Unable to get run control start time, IOC has not started yet", "MINOR")
        except ValueError as e:
            latest_ioc_start = None
            print_and_log("Unable to format ioc start time: {0}".format(e), "MAJOR")

        return latest_ioc_start

    def _invalid_ioc_start_time(self, latest_ioc_start):
        """
        Check is this start time is invalid.

        This checks if it was successfully parsed and whether it is less than
        the current run control IOC start time.

        Args:
            latest_ioc_start (datetime): time to check

        Returns:
            Bool whether the parsed datetime is valid

        """
        return latest_ioc_start is None or (self._rc_ioc_start_time is
                                            not None and latest_ioc_start
                                            <= self._rc_ioc_start_time)

    def wait_for_ioc_start(self, time_between_tries=2):
        """
        Wait for the run-control IOC to start.

        Args:
            time_between_tries (int): time to wait before checking if run
                control has started

        """
        print_and_log("Waiting for runcontrol IOC to start ...")

        for loop_count in range(MAX_LOOPS_TO_WAIT_FOR_START):

            restart_pending = ioc_restart_pending(self._prefix + RC_IOC_PREFIX,
                                                  self._channel_access)

            latest_ioc_start = self._get_latest_ioc_start()
            start_time_invalid = self._invalid_ioc_start_time(latest_ioc_start)

            if restart_pending or start_time_invalid:
                sleep(time_between_tries)
            else:
                self._rc_ioc_start_time = latest_ioc_start
                break
        else:
            print_and_log("Runcontrol appears not to have started", "MAJOR")

    def _start_ioc(self):
        """
        Start the IOC.
        """
        try:
            self._ioc_control.start_ioc(RUNCONTROL_IOC)
        except Exception as err:
            print_and_log("Problem with starting the run-control IOC: %s"
                          % str(err), "MAJOR")

    def restart_ioc(self, clear_autosave):
        """
        Restarts the IOC.

        Args:
            clear_autosave (bool): Whether to delete the autosave files first

        """
        if clear_autosave:
            print_and_log("Removing the run-control autosave files")
            self._run_control_auto_save_helper.clear_autosave_files()
        else:
            print_and_log("Reusing the existing run-control autosave files")

        try:
            self._ioc_control.restart_ioc(RUNCONTROL_IOC, force=True)
        except Exception as err:
            print_and_log("Problem with restarting the run-control IOC: %s"
                          % str(err), "MAJOR")
