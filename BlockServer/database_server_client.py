from server_common.utilities import dehex_and_decompress
import json
from server_common.channel_access import caget


class DatabaseServerClient(object):
    def __init__(self, blockserver_prefix):
        self._blockserver_prefix = blockserver_prefix

    def get_iocs(self):
        # Get IOCs from DatabaseServer
        rawjson = dehex_and_decompress(caget(self._blockserver_prefix + "IOCS"))
        return json.loads(rawjson).keys()
