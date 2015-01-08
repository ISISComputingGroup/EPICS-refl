class IocOptions(object):
    """Contains the possible macros and pvsets of an IOC"""
    # TODO: inheritance relation with other IOC container?
    def __init__(self, name, macros=None, pvsets=None, pvs=None):
        if macros is None:
            self.macros = dict()
        else:
            self.macros = macros

        if pvsets is None:
            self.pvsets = dict()
        else:
            self.pvsets = pvsets

        if pvsets is None:
            self.pvs = dict()
        else:
            self.pvs = pvs

        self.name = name

    def dict_to_list(self, in_dict):
        # Convert into format for better GUI parsing (I know it's messy but it's what the GUI wants)
        out_list = []
        for k, v in in_dict.iteritems():
            v['name'] = k
            out_list.append(v)
        return out_list

    def to_dict(self):
        return {'macros': self.dict_to_list(self.macros), 'pvsets': self.dict_to_list(self.pvsets),
                'pvs': self.dict_to_list(self.pvs)}
