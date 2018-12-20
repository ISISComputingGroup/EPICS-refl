from server_common.utilities import dehex_and_decompress, print_and_log
from server_common.channel_access import ChannelAccess
from server_common.pv_names import DatabasePVNames
import json


def get_iocs():
    # Get the list of available IOCs from DatabaseServer
    try:
        rawjson = dehex_and_decompress(ChannelAccess.caget(DatabasePVNames.IOCS))
        return json.loads(rawjson).keys()
    except Exception as err:
        print_and_log("Could not retrieve IOC list: {}".format(err), "MAJOR")
        return []