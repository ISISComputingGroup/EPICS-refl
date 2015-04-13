from BlockServer.core.macros import PVPREFIX_MACRO


class Block(object):
    """ Contains all the information about a block.

        Attributes:
            name (string) : The block name
            pv (string) : The PV pointed at
            local (bool) : Whether the PV is local to the instrument
            visible (bool) : Whether the block should be shown
            subconfig (string) : The component the block belongs to
            save_rc (bool) : Whether to save the run-control settings
            runcontrol (bool) : Whether run-control is enabled
            lowlimt (float) : The low limit for run-control
            highlimit (float) : The high limit for run-control
    """
    def __init__(self, name, pv, local=True, visible=True, subconfig=None, save_rc=False,
                 runcontrol=False, lowlimit=None, highlimit=None):
        """ Constructor.

        Args:
            name (string) : The block name
            pv (string) : The PV pointed at
            local (bool) : Whether the PV is local to the instrument
            visible (bool) : Whether the block should be shown
            subconfig (string) : The component the block belongs to
            save_rc (bool) : Whether to save the run-control settings
            runcontrol (bool) : Whether run-control is enabled
            lowlimt (float) : The low limit for run-control
            highlimit (float) : The high limit for run-control
        """
        self.name = name
        self.pv = pv
        self.local = local
        self.visible = visible
        self.subconfig = subconfig
        self.save_rc_settings = save_rc
        self.rc_lowlimit = lowlimit
        self.rc_highlimit = highlimit
        self.rc_enabled = runcontrol

    def _get_pv(self):
        pv_name = self.pv
        # Check starts with as may have already been provided
        if self.local and not pv_name.startswith(PVPREFIX_MACRO):
            pv_name = PVPREFIX_MACRO + self.pv
        return pv_name

    def set_visibility(self, visible):
        """ Toggle the visibility of the block.

        Args:
            visible (bool) : Whether the block is visible or not
        """
        self.visible = visible

    def __str__(self):
        data = "Name: %s, PV: %s, Local: %s, Visible: %s, Subconfig: %s" \
               % (self.name, self.pv, self.local, self.visible, self.subconfig)
        data += ", SaveRC: %s, RCEnabled: %s, RCLow: %s, RCHigh: %s" \
                % (self.save_rc_settings, self.rc_enabled, self.rc_lowlimit, self.rc_highlimit)
        return data

    def to_dict(self):
        """ Puts the block's details into a dictionary.

        Returns:
            dict : The block's details
        """
        return {"name": self.name, "pv": self._get_pv(), "local": self.local,
                "visible": self.visible, "subconfig": self.subconfig}


class Group(object):
    """ Represents a group.

        Attributes:
            name (string) : The name of the group
            blocks (dict) : The blocks that are in the group
            subconfig (string) : The component the group belongs to
    """
    def __init__(self, name, subconfig=None):
        """ Constructor.

        Args:
            name (string) : The name for the group
            subconfig (string) : The component to which the group belongs
        """
        self.name = name
        self.blocks = []
        self.subconfig = subconfig

    def __str__(self):
        data = "Name: %s, Subconfig: %s, Blocks: %s" % (self.name, self.subconfig, self.blocks)
        return data

    def to_dict(self):
        """ Puts the group's details into a dictionary.

        Returns:
            dict : The group's details
        """
        return {'name': self.name, 'blocks': self.blocks, "subconfig": self.subconfig}


class IOC(object):
    """ Represents an IOC.

    Attributes:
        name (string) : The name of the IOC
        autostart (bool) : Whether the IOC should automatically start
        restart (bool) : Whether the IOC should automatically restart
        subconfig (string) : The component the IOC belongs to
        macros (dict) : The IOC's macros
        pvs (dict) : The IOC's PVs
        pvsets (dict) : The IOC's PV sets
        simlevel (string) : The level of simulation
    """
    def __init__(self, name, autostart=True, restart=True, subconfig=None, macros=None, pvs=None, pvsets=None,
                 simlevel=None):
        """ Constructor.

        Args:
            name (string) : The name of the IOC
            autostart (bool) : Whether the IOC should automatically start
            restart (bool) : Whether the IOC should automatically restart
            subconfig (string) : The component the IOC belongs to
            macros (dict) : The IOC's macros
            pvs (dict) : The IOC's PVs
            pvsets (dict) : The IOC's PV sets
            simlevel (string) : The level of simulation
        """
        self.name = name
        self.autostart = autostart
        self.restart = restart
        self.subconfig = subconfig

        if simlevel is None:
            self.simlevel = "None"
        else:
            self.simlevel = simlevel

        if macros is None:
            self.macros = dict()
        else:
            self.macros = macros

        if pvs is None:
            self.pvs = dict()
        else:
            self.pvs = pvs

        if pvsets is None:
            self.pvsets = dict()
        else:
            self.pvsets = pvsets

    def _dict_to_list(self, in_dict):
        """ Converts into a format better for the GUI to parse, namely a list.

        It's messy but it's what the GUI wants.

        Args:
            in_dict (dict) : The dictionary to be converted

        Returns:
            list : The newly created list
        """
        out_list = []
        for k, v in in_dict.iteritems():
            v['name'] = k
            out_list.append(v)
        return out_list

    def __str__(self):
        data = "Name: %s, Subconfig: %s" % (self.name, self.subconfig)
        return data

    def to_dict(self):
        """ Puts the IOC's details into a dictionary.

        Returns:
            dict : The IOC's details
        """
        return {'name': self.name, 'autostart': self.autostart, 'restart': self.restart,
                'simlevel': self.simlevel, 'pvs': self._dict_to_list(self.pvs),
                'pvsets': self._dict_to_list(self.pvsets), 'macros': self._dict_to_list(self.macros),
                'subconfig': self.subconfig}


class MetaData(object):
    """Represents the metadata from a configuration/component.

    Attributes:
        name (string) : The name of the configuration
        pv (string) : The PV for the configuration
        description (string) : The description
        history (list) : The save history of the configuration
    """
    def __init__(self, config_name, pv_name="", description=""):
        """ Constructor.

        Args:
            config_name (string) : The name of the configuration
            pv (string) : The PV for the configuration
            description (string) : The description
        """
        self.name = config_name
        self.pv = pv_name
        self.description = description
        self.history = []

    def to_dict(self):
        """ Puts the metadata into a dictionary.

        Returns:
            dict : The metadata
        """
        return {'name': self.name, 'pv': self.pv, 'description': self.description, 'history': self.history}