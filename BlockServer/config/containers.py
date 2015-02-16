from BlockServer.macros import PVPREFIX_MACRO


class Block(object):
    """Contains all the information about a block"""
    def __init__(self, name, pv, local=True, visible=True, subconfig=None, save_rc=False,
                 runcontrol=False, lowlimit=None, highlimit=None):
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
        self.visible = visible

    def __str__(self):
        data = "Name: %s, PV: %s, Local: %s, Visible: %s, Subconfig: %s" \
               % (self.name, self.pv, self.local, self.visible, self.subconfig)
        data += ", SaveRC: %s, RCEnabled: %s, RCLow: %s, RCHigh: %s" \
                % (self.save_rc_settings, self.rc_enabled, self.rc_lowlimit, self.rc_highlimit)
        return data

    def to_dict(self):
        return {"name": self.name, "pv": self._get_pv(), "local": self.local,
                "visible": self.visible, "subconfig": self.subconfig}


class Group(object):
    """Represents a group"""
    def __init__(self, name, subconfig=None):
        self.name = name
        self.blocks = []
        self.subconfig = subconfig

    def __str__(self):
        data = "Name: %s, Subconfig: %s, Blocks: %s" % (self.name, self.subconfig, self.blocks)
        return data

    def to_dict(self):
        return {'name': self.name, 'blocks': self.blocks, "subconfig": self.subconfig}


class IOC(object):
    """Represents an IOC"""
    #TODO: Get methods are messy?
    #TODO: _ under private variables
    def __init__(self, name, autostart=True, restart=True, subconfig=None, macros=None, pvs=None, pvsets=None, simlevel=None):
        self.name = name

        self.autostart = autostart
        self.restart = restart
        self.subconfig = subconfig

        if simlevel == None:
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

    def dict_to_list(self, in_dict):
        #convert into format for better GUI parsing (I know it's messy but it's what the GUI wants)
        out_list = []
        for k, v in in_dict.iteritems():
            v['name'] = k
            out_list.append(v)
        return out_list

    def __str__(self):
        data = "Name: %s, Subconfig: %s" % (self.name, self.subconfig)
        return data

    def to_dict(self):
        return {'name': self.name, 'autostart': self.autostart, 'restart': self.restart,
                'simlevel': self.simlevel, 'pvs': self.dict_to_list(self.pvs),
                'pvsets': self.dict_to_list(self.pvsets), 'macros': self.dict_to_list(self.macros),
                'subconfig': self.subconfig}

class MetaData(object):
    """Represents the metadata from a config"""

    def __init__(self, config_name, pv_name="", description=""):
        self.name = config_name
        self.pv = pv_name
        self.description = description
        self.history = []

    def to_dict(self):
        return {'name': self.name, 'pv': self.pv, 'description': self.description, 'history': self.history}