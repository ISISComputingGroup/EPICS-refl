from BlockServer.core.macros import PVPREFIX_MACRO
import copy


class Block(object):
    """ Contains all the information about a block.

        Attributes:
            name (string): The block name
            pv (string): The PV pointed at
            local (bool): Whether the PV is local to the instrument
            visible (bool): Whether the block should be shown
            subconfig (string): The component the block belongs to

            runcontrol (bool): Whether run-control is enabled
            lowlimt (float): The low limit for run-control
            highlimit (float): The high limit for run-control

            arch_periodic (bool): Whether the block is sampled periodically in the archiver
            arch_rate (float): Time between archive samples (in seconds)
            arch_deadband (float): Deadband for the block to be archived
    """
    def __init__(self, name, pv, local=True, visible=True, subconfig=None, runcontrol=False, lowlimit=None,
                 highlimit=None, log_periodic=False, log_rate=5, log_deadband=0):
        """ Constructor.

        Args:
            name (string): The block name
            pv (string): The PV pointed at
            local (bool): Whether the PV is local to the instrument
            visible (bool): Whether the block should be shown
            subconfig (string): The component the block belongs to

            runcontrol (bool): Whether run-control is enabled
            lowlimt (float): The low limit for run-control
            highlimit (float): The high limit for run-control

            arch_periodic (bool): Whether the block is sampled periodically in the archiver
            arch_rate (float): Time between archive samples (in seconds)
            arch_deadband (float): Deadband for the block to be archived
        """
        self.name = name
        self.pv = pv
        self.local = local
        self.visible = visible
        self.subconfig = subconfig
        self.rc_lowlimit = lowlimit
        self.rc_highlimit = highlimit
        self.rc_enabled = runcontrol
        self.log_periodic = log_periodic
        self.log_rate = log_rate
        self.log_deadband = log_deadband

    def _get_pv(self):
        pv_name = self.pv
        # Check starts with as may have already been provided
        if self.local and not pv_name.startswith(PVPREFIX_MACRO):
            pv_name = PVPREFIX_MACRO + self.pv
        return pv_name

    def set_visibility(self, visible):
        """ Toggle the visibility of the block.

        Args:
            visible (bool): Whether the block is visible or not
        """
        self.visible = visible

    def __str__(self):
        data = "Name: %s, PV: %s, Local: %s, Visible: %s, Subconfig: %s" \
               % (self.name, self.pv, self.local, self.visible, self.subconfig)
        data += ", RCEnabled: %s, RCLow: %s, RCHigh: %s" \
                % (self.rc_enabled, self.rc_lowlimit, self.rc_highlimit)
        return data

    def to_dict(self):
        """ Puts the block's details into a dictionary.

        Returns:
            dict : The block's details
        """
        return {"name": self.name, "pv": self._get_pv(), "local": self.local,
                "visible": self.visible, "subconfig": self.subconfig, "runcontrol": self.rc_enabled,
                "lowlimit": self.rc_lowlimit, "highlimit": self.rc_highlimit,
                "log_periodic": self.log_periodic, "log_rate": self.log_rate, "log_deadband": self.log_deadband}

