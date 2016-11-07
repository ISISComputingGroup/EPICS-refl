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
from time import sleep

from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, TAG_RC_ENABLE, TAG_RC_OUT_LIST
from server_common.utilities import print_and_log
from BlockServer.core.on_the_fly_pv_interface import OnTheFlyPvInterface
from server_common.utilities import print_and_log, compress_and_hex, check_pv_name_valid, create_pv_name, \
    convert_to_json, convert_from_json
from server_common.channel_access import ChannelAccess
from BlockServer.core.pv_names import BlockserverPVNames


TAG_RC_DICT = {"LOW": TAG_RC_LOW, "HIGH": TAG_RC_HIGH, "ENABLE": TAG_RC_ENABLE}
RC_RESET_PV = "CS:IOC:RUNCTRL_01:DEVIOS:SysReset"
RC_RESTART_PV = "CS:PS:RUNCTRL_01:RESTART"
RUNCONTROL_SETTINGS = "rc_settings.cmd"
AUTOSAVE_DIR = "autosave"
RUNCONTROL_IOC = "RUNCTRL_01"

RUNCONTROL_OUT_PV = BlockserverPVNames.prepend_blockserver('GET_RC_OUT')
RUNCONTROL_GET_PV = BlockserverPVNames.prepend_blockserver('GET_RC_PARS')


class RunControlManager(OnTheFlyPvInterface):
    """A class for taking care of setting up run-control.
    """
    def __init__(self, prefix, config_dir, var_dir, ioc_control, active_configholder, block_server,
                 channel_access=ChannelAccess()):
        """Constructor.

        Args:
            prefix (string): The instrument prefix
            config_dir (string): The root of the configuration directory
            var_dir (string): The root of the VAR directory
            ioc_control (IocControl): The object for restarting the IOC
            active_configholder (ActiveConfigHolder): The current configuration
            block_server (BlockServer): A reference to the BlockServer instance
            channel_access (ChannelAccess): A reference to the ChannelAccess instance
        """
        self._prefix = prefix
        self._settings_file = os.path.join(config_dir, RUNCONTROL_SETTINGS)
        self._autosave_dir = os.path.join(var_dir, AUTOSAVE_DIR, RUNCONTROL_IOC)
        self._block_prefix = prefix + "CS:SB:"
        self._stored_settings = None
        self._ioc_control = ioc_control
        self._active_configholder = active_configholder
        self._bs = block_server
        self._pvs_to_read = [RUNCONTROL_GET_PV, RUNCONTROL_OUT_PV]
        self._create_standard_pvs()
        self._channel_access = channel_access
        print "RUNCONTROL SETTINGS FILE: %s" % self._settings_file
        print "RUNCONTROL AUTOSAVE DIRECTORY: %s" % self._autosave_dir
        self._intialise_runcontrol_ioc()

    def read_pv_exists(self, pv):
        return pv in self._pvs_to_read

    def write_pv_exists(self, pv):
        return False

    def handle_pv_write(self, pv, data):
        # Nothing to write
        pass

    def handle_pv_read(self, pv):
        if pv == RUNCONTROL_GET_PV:
            js = convert_to_json(self.get_current_settings())
            value = compress_and_hex(js)
            return value
        elif pv == RUNCONTROL_OUT_PV:
            js = convert_to_json(self.get_out_of_range_pvs())
            value = compress_and_hex(js)
            return value
        return ""

    def update_monitors(self):
        # No monitors
        pass

    def initialise(self, full_init=False):
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

    def create_runcontrol_pvs(self, clear_autosave):
        """ Create the PVs for run-control.

        Configures the run-control IOC to have PVs for the current configuration.

        Args:
            clear_autosave: Whether to remove any values stored by autosave
        """
        self.update_runcontrol_blocks(self._active_configholder.get_block_details())
        self.restart_ioc(clear_autosave)
        # Need to wait for RUNCONTROL_IOC to restart
        self.wait_for_ioc_start()
        self.restore_config_settings(self._active_configholder.get_block_details())

    def update_runcontrol_blocks(self, blocks):
        """Update the run-control settings in the run-control IOC with the current blocks.

        Args:
            blocks (OrderedDict): The blocks that are part of the current configuration
        """
        f = None
        try:
            f = open(self._settings_file, 'w')
            for bn, blk in blocks.iteritems():
                f.write('dbLoadRecords("$(RUNCONTROL)/db/runcontrol.db","P=$(MYPVPREFIX),PV=$(MYPVPREFIX)CS:SB:%s")\n'
                        % blk.name)
            # Need an extra blank line
            f.write("\n")
        except Exception as err:
            print err
        finally:
            if f is not None:
                f.close()

    def get_out_of_range_pvs(self):
        """Get a list of PVs that are currently out of range.

        This may include PVs that are not blocks, but have had run-control settings applied directly

        Returns:
            list : A list of PVs that are out of range
        """
        raw = self._channel_access.caget(self._prefix + TAG_RC_OUT_LIST, True).strip()
        raw = raw.split(" ")
        if raw is not None and len(raw) > 0:
            ans = list()
            for i in raw:
                if len(i) > 0:
                    ans.append(i)
            return ans
        else:
            return list()

    def get_current_settings(self):
        """ Returns the current run-control settings

        Returns:
            dict : The current run-control settings
        """
        blocks = self._active_configholder.get_block_details()
        settings = dict()
        for bn, blk in blocks.iteritems():
            low = self._channel_access.caget(self._block_prefix + blk.name + TAG_RC_LOW)
            high = self._channel_access.caget(self._block_prefix + blk.name + TAG_RC_HIGH)
            enable = self._channel_access.caget(self._block_prefix + blk.name + TAG_RC_ENABLE, True)
            if enable == "YES":
                enable = True
            else:
                enable = False
            settings[blk.name] = {"LOW": low, "HIGH": high, "ENABLE": enable}
        return settings

    def restore_config_settings(self, blocks):
        """Restore run-control settings based on what is stored in a configuration.

        Args:
            blocks (OrderedDict): The blocks for the configuration
        """
        for n, blk in blocks.iteritems():
            settings = dict()
            if blk.rc_enabled:
                settings["ENABLE"] = True
            else:
                settings["ENABLE"] = False
            if blk.rc_lowlimit is not None:
                settings["LOW"] = blk.rc_lowlimit
            if blk.rc_highlimit is not None:
                settings["HIGH"] = blk.rc_highlimit
            self._set_rc_values(blk.name, settings)

    def set_runcontrol_settings(self, data):
        """ Replaces the run-control settings with new values.

        Args:
            data (dict): The new run-control settings to set (dictionary of dictionaries)
        """
        for bn, settings in data.iteritems():
            if settings is not None:
                self._set_rc_values(bn, settings)

    def _set_rc_values(self, bn, settings):
        for key, value in settings.iteritems():
            if key.upper() in TAG_RC_DICT.keys():
                try:
                    self._channel_access.caput(self._block_prefix + bn + TAG_RC_DICT[key.upper()], value)
                except Exception as err:
                    print_and_log("Problem with setting runcontrol for %s: %s" % (bn, err))

    def wait_for_ioc_start(self):
        """Waits for the run-control IOC to start."""
        # TODO: Give up after a bit
        print_and_log("Waiting for runcontrol IOC to start")
        while True:
            # See if the IOC has restarted by looking for a standard PV
            try:
                running = True if self._channel_access.caget(self._prefix + RC_RESET_PV) is not None else False
                restart_pending = True if self._channel_access.caget(self._prefix + RC_RESTART_PV) is "Busy" else False
                started = running and not restart_pending
            except Exception as err:
                # Probably has timed out
                started = False
            if started:
                print_and_log("Runcontrol IOC started")
                break
            sleep(2)

    def _start_ioc(self):
        """Start the IOC."""
        try:
            self._ioc_control.start_ioc(RUNCONTROL_IOC)
        except Exception as err:
            print_and_log("Problem with starting the run-control IOC: %s" % str(err), "MAJOR")

    def restart_ioc(self, clear_autosave):
        """ Restarts the IOC.

        Args:
            clear_autosave (bool): Whether to delete the autosave files first
        """
        if clear_autosave:
            print_and_log("Removing the run-control autosave files")
            self._clear_autosave_files()
        else:
            print_and_log("Reusing the existing run-control autosave files")

        try:
            self._ioc_control.restart_ioc(RUNCONTROL_IOC, force=True, reapply_auto=False)
        except Exception as err:
            print_and_log("Problem with restarting the run-control IOC: %s" % str(err), "MAJOR")

    def _clear_autosave_files(self):
        for fname in os.listdir(self._autosave_dir):
            file_path = os.path.join(self._autosave_dir, fname)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as err:
                print_and_log("Problem deleting autosave files for the run-control IOC: %s" % str(err), "MAJOR")
