class IocOptions(object):
    """Contains the possible macros and pvsets of an IOC"""
    def __init__(self, name, macros=None, pvsets=None, pvs=None):
        """Constructor

        Args:
            name (str) : The name of the IOC the options are associated with
            macros (dict, optional) : A dict of the possible macros for the IOC, along with a list of associated
                                      parameters (description, pattern etc.)
            pvsets (dict, optional) : A dict of the possible pvsets for the IOC, along with a list of associated
                                      parameters (description etc.)
            pvs (dict, optional) : A dict of the possible pvs for the IOC, along with a list of associated parameters
                                   (description etc.)
        """
        if macros is None:
            self.macros = dict()
        else:
            self.macros = macros

        if pvsets is None:
            self.pvsets = dict()
        else:
            self.pvsets = pvsets

        if pvs is None:
            self.pvs = dict()
        else:
            self.pvs = pvs

        self.name = name

    def _dict_to_list(self, in_dict):
        # Convert into format for better GUI parsing (I know it's messy but it's what the GUI wants)
        out_list = []
        for k, v in in_dict.iteritems():
            v['name'] = k
            out_list.append(v)
        return out_list

    def to_dict(self):
        """Get a dictionary of the possible macros and pvsets for an IOC

        Returns:
            dict : Possible macros and pvsets
        """
        return {'macros': self._dict_to_list(self.macros), 'pvsets': self._dict_to_list(self.pvsets),
                'pvs': self._dict_to_list(self.pvs)}
