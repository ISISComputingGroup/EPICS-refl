from __future__ import print_function, unicode_literals, division, absolute_import

import functools
import sys
import os

from concurrent.futures import ThreadPoolExecutor
from genie_python.channel_access_exceptions import UnableToConnectToPVException, ReadAccessException
from genie_python.genie_cachannel_wrapper import CaChannelWrapper

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import print_and_log as _common_print_and_log


THREADPOOL = ThreadPoolExecutor()

__all__ = ['print_and_log', 'get_hostname_from_prefix', 'THREADPOOL']

print_and_log = functools.partial(_common_print_and_log, src="REMIOC")


def get_hostname_from_prefix(pv_prefix):
    """
    DevIocStats on any IOC publishes the hostname of the computer it's running on over channel access.
    """
    try:
        # Choose an IOC which should always be up (INSTETC) and use the deviocstats hostname record.
        name = CaChannelWrapper.get_pv_value("{}CS:IOC:INSTETC_01:DEVIOS:HOSTNAME".format(pv_prefix),
                                             to_string=True, timeout=5)
        print_and_log("get_hostname_from_prefix: hostname is '{}' (from DevIocStats)".format(name))
        return name
    except (UnableToConnectToPVException, ReadAccessException) as e:
        print_and_log("get_hostname_from_prefix: Unable to get hostname because {}.".format(e))
        return None
