from time import sleep

from server_common.channel_access import caget, caput
from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, TAG_RC_ENABLE, TAG_RC_OUT_LIST
from server_common.utilities import print_and_log


TAG_RC_DICT = {"LOW": TAG_RC_LOW, "HIGH": TAG_RC_HIGH, "ENABLE": TAG_RC_ENABLE}
RC_PV = "CS:IOC:RUNCTRL_01:DEVIOS:SysReset"


class RunControlManager(object):
    """A class for taking care of setting up run-control.
    """
    def __init__(self, prefix, settings_dir):
        """Constructor.

        Args:
            prefix (string) : The instrument prefix
            settings_dir (string) : The location for the run-control settings file
        """
        self._prefix = prefix
        self._settings_dir = settings_dir
        self._block_prefix = prefix + "CS:SB:"
        self._stored_settings = None

    def update_runcontrol_blocks(self, blocks):
        """Update the run-control settings in the run-control IOC with the current blocks.

        Args:
            blocks (OrderedDict) : The blocks that are part of the current configuration
        """
        f = None
        try:
            f = open(self._settings_dir, 'w')
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
        raw = caget(self._prefix + TAG_RC_OUT_LIST, True).strip()
        raw = raw.split(" ")
        if raw is not None and len(raw) > 0:
            ans = list()
            for i in raw:
                if len(i) > 0:
                    ans.append(i)
            return ans
        else:
            return []

    def get_runcontrol_settings(self, blocks):
        """ Returns the current run-control settings

        Returns:
            dict : The current run-control settings
        """
        settings = dict()
        for bn, blk in blocks.iteritems():
            low = caget(self._block_prefix + blk.name + TAG_RC_LOW)
            high = caget(self._block_prefix + blk.name + TAG_RC_HIGH)
            enable = caget(self._block_prefix + blk.name + TAG_RC_ENABLE)
            if enable == "YES":
                enable = True
            else:
                enable = False
            settings[blk.name] = {"LOW": low, "HIGH": high, "ENABLE": enable}
        return settings

    def restore_config_settings(self, blocks):
        """Restore run-control settings based on what is stored in a configuration.

        Args:
            blocks (OrderedDict) : The blocks for the configuration
        """
        for n, blk in blocks.iteritems():
            print blk
            if blk.save_rc_settings:
                settings = dict()
                if blk.rc_enabled:
                    settings["ENABLE"] = "YES"
                else:
                    settings["ENABLE"] = "NO"
                if blk.rc_lowlimit is not None:
                    settings["LOW"] = blk.rc_lowlimit
                if blk.rc_highlimit is not None:
                    settings["HIGH"] = blk.rc_highlimit
                self._set_rc_values(blk.name, settings)

    def set_runcontrol_settings(self, data):
        """ Replaces the runc-control settings with new values.

        Args:
            data (dict) : The new run-control settings to set (dictionary of dictionaries)
        """
        for bn, settings in data.iteritems():
            if settings is not None:
                self._set_rc_values(bn, settings)

    def _set_rc_values(self, bn, settings):
        for key, value in settings.iteritems():
            if key.upper() in TAG_RC_DICT.keys():
                try:
                    caput(self._block_prefix + bn + TAG_RC_DICT[key.upper()], value)
                except Exception as err:
                    print_and_log("Problem with setting runcontrol for %s: %s" % (bn, err))

    def wait_for_ioc_start(self):
        """Waits for the run-control IOC to start."""
        print_and_log("Waiting for runcontrol IOC to start")
        while True:
            sleep(2)
            # See if the IOC has restarted by looking for a standard PV
            try:
                ans = caget(self._prefix + RC_PV)
            except Exception as err:
                # Probably has timed out
                ans = None
            if ans is not None:
                print_and_log("Runcontrol IOC started")
                break
