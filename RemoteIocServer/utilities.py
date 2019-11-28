from __future__ import print_function, unicode_literals, division, absolute_import

import functools
import sys
import os

from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import print_and_log as _common_print_and_log
from server_common.channel_access import ChannelAccess


CONFIG_DIR = os.getenv("ICPCONFIGROOT")


THREADPOOL = ThreadPoolExecutor()

__all__ = ['print_and_log', 'get_hostname_from_prefix', 'THREADPOOL']

print_and_log = functools.partial(_common_print_and_log, src="REMIOC")


def get_hostname_from_prefix(pv_prefix):
    """
    DevIocStats on any IOC publishes the hostname of the computer it's running on over channel access.
    """
    pv_name = "{}CS:IOC:INSTETC_01:DEVIOS:HOSTNAME".format(pv_prefix)
    name = ChannelAccess.caget(pv_name, as_string=True, timeout=5)
    if name is None:
        print_and_log("get_hostname_from_prefix: Unable to get hostname because of error reading pv {}.".format(
            pv_name))
    else:
        print_and_log("get_hostname_from_prefix: hostname is '{}' (from DevIocStats)".format(name))
    return name


def read_startup_file():
    """
    Reads the configuration file in <config dir>/startup.txt and returns a list of IOC names.
    """
    with open(os.path.join(CONFIG_DIR, "startup.txt")) as f:
        return [name.strip() for name in f.readlines() if name.strip() != ""]
