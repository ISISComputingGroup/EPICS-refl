import json
from collections import OrderedDict

from containers import Group
from constants import GRP_NONE


class ConfigurationJsonConverter(object):
    """Converts configuration data to and from JSON"""

    @staticmethod
    def _blocks_to_dict(blocks):
        blks = OrderedDict()
        if blocks is not None:
            for block in blocks.values():
                blks[block.name] = block.to_dict()
        return blks

    @staticmethod
    def _groups_to_list(groups):
        grps = list()
        if groups is not None:
            for group in groups.values():
                if group.name.lower() != GRP_NONE.lower():
                    grps.append({"name": group.name, "subconfig": group.subconfig, "blocks": group.blocks})

            # Add NONE group at end
            if GRP_NONE.lower() in groups.keys():
                grps.append({"name": GRP_NONE, "subconfig": None, "blocks": groups[GRP_NONE.lower()].blocks})
        return grps

    @staticmethod
    def groups_to_json(groups):
        grps = ConfigurationJsonConverter._groups_to_list(groups)
        return json.dumps(grps)

    @staticmethod
    def groups_from_json(js):
        a = json.loads(js)
        return a

    @staticmethod
    def _iocs_to_list(iocs):
        ioc_list = list()
        if iocs is not None:
            for name, ioc in iocs.iteritems():
                ioc_list.append(ioc.to_dict())
        return ioc_list

    @staticmethod
    def _comps_to_list(components):
        comps = list()
        if components is not None:
            for name, comp in components.iteritems():
                d = {'name': comp.name}
                comps.append(d)
        return comps

    @staticmethod
    def config_to_json(pv_prefix, blocks, groups, iocs, components):
        """Converts a dictionary made up of a configuration into JSON"""
        config = dict()
        config['blocks'] = ConfigurationJsonConverter._blocks_to_dict(blocks)
        config['groups'] = ConfigurationJsonConverter._groups_to_list(groups)
        config['iocs'] = ConfigurationJsonConverter._iocs_to_list(iocs)
        config['components'] = ConfigurationJsonConverter._comps_to_list(components)
        return json.dumps(config)



