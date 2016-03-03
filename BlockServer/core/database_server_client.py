from server_common.utilities import dehex_and_decompress
import json
from server_common.channel_access import caget


class DatabaseServerClient(object):
    """Class for talking to the DatabaseServer.
    """
    def __init__(self, blockserver_prefix):
        """ Constructor.

        Args:
            blockserver_prefix (string): The prefix for the BlockServer
        """
        self._blockserver_prefix = blockserver_prefix

    def get_iocs(self):
        """ Get a list of IOCs from DatabaseServer.

        Returns:
            list : A list of IOC names
        """
        rawjson = dehex_and_decompress(caget(self._blockserver_prefix + "IOCS"))
        return json.loads(rawjson).keys()
