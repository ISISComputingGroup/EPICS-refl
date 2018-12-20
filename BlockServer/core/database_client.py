"""
Functions for interacting with the database server.
"""
from server_common.utilities import dehex_and_decompress, print_and_log
from server_common.channel_access import ChannelAccess
from server_common.pv_names import DatabasePVNames
import json


def get_iocs(prefix):
    """
    Get the list of available IOCs from DatabaseServer.

    Args:
        prefix : The PV prefix for this instrument.

    Returns:
        A list of the names of available IOCs.
    """
    #
    try:
        rawjson = dehex_and_decompress(ChannelAccess.caget(prefix + DatabasePVNames.IOCS))
        return json.loads(rawjson).keys()
    except Exception as err:
        print_and_log("Could not retrieve IOC list: {}".format(err), "MAJOR")
        return []