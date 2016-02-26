import json
from collections import OrderedDict

from BlockServer.core.constants import GRP_NONE


class ConfigurationJsonConverter(object):
    """Helper class for converting configuration data to and from JSON.

    Consists of static methods only.

    """

    @staticmethod
    def _groups_to_list(groups):
        grps = list()
        if groups is not None:
            for group in groups.values():
                if group.name.lower() != GRP_NONE.lower():
                    grps.append({"name": group.name, "component": group.component, "blocks": group.blocks})

            # Add NONE group at end
            if GRP_NONE.lower() in groups.keys():
                grps.append({"name": GRP_NONE, "component": None, "blocks": groups[GRP_NONE.lower()].blocks})
        return grps

    @staticmethod
    def groups_to_json(groups):
        """ Converts the groups dictionary to a JSON list

        Args:
            groups (OrderedDict) : The groups to convert to JSON

        Returns:
            string : The groups as a JSON list
        """
        grps = ConfigurationJsonConverter._groups_to_list(groups)
        return json.dumps(grps)
