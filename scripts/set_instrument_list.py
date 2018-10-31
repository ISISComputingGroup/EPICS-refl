# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import json
import zlib
import sys
import os
try:
    from server_common.channel_access import ChannelAccess as ca
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(sys.path[0])))  # to allow server common from dir below
    from server_common.channel_access import ChannelAccess as ca


def compress_and_hex(value):
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    return zlib.decompress(value.decode("hex"))


def set_env():
    epics_ca_addr_list = "EPICS_CA_ADDR_LIST"
    """ If we're not in an EPICS terminal, add the address list to the set of
    environment keys """
    if not epics_ca_addr_list in os.environ.keys():
        os.environ[epics_ca_addr_list] = "127.255.255.255 130.246.51.255"
    print(epics_ca_addr_list + " = " + str(os.environ.get(epics_ca_addr_list)))


def inst_dictionary(instrument_name, hostname_prefix="NDX", hostname=None, pv_prefix=None, is_scheduled=True):
    """
    Generate the instrument dictionary for the instrument list
    Args:
        instrument_name: instrument name
        hostname_prefix: prefix for hostname (defaults to NDX)
        hostname: whole host name overrides prefix, defaults to hostname_prefix + instrument name
        pv_prefix: the pv prefeix; default to IN:instrument_name
        is_scheduled: whether the instrument has scheduled users and so should have user details written to it; default to True

    Returns: dictionary for instrument

    """
    if hostname is not None:
        hostname_to_use = hostname
    else:
        hostname_to_use = hostname_prefix + instrument_name
    if pv_prefix is not None:
        pv_prefix_to_use = pv_prefix
    else:
        pv_prefix_to_use = "IN:{0}:".format(instrument_name)
    return {"name": instrument_name,
            "hostName": hostname_to_use,
            "pvPrefix": pv_prefix_to_use,
            "isScheduled": is_scheduled}


if __name__ == "__main__":
    set_env()

    # The PV address list
    pv_address = "CS:INSTLIST"

    # instrument list values to set (uses utility to return the dictionary but you can use a dictionary directly)
    instruments_list = [
        inst_dictionary("LARMOR"),
        inst_dictionary("ALF"),
        inst_dictionary("DEMO", is_scheduled=False),
        inst_dictionary("IMAT"),
        inst_dictionary("MUONFE", hostname_prefix="NDE", is_scheduled=False),
        inst_dictionary("ZOOM"),
        inst_dictionary("IRIS"),
        inst_dictionary("IRIS_SETUP", pv_prefix="IN:IRIS_S29:", is_scheduled=False),
        inst_dictionary("HRPD"),
        inst_dictionary("POLARIS"),
        inst_dictionary("VESUVIO"),
        inst_dictionary("ENGINX"),
        inst_dictionary("MERLIN"),
        inst_dictionary("RIKENFE", is_scheduled=False),
        inst_dictionary("SELAB", is_scheduled=False),
        inst_dictionary("EMMA-A", is_scheduled=False),
        inst_dictionary("SANDALS"),
        inst_dictionary("GEM"),
        inst_dictionary("MAPS"),
        inst_dictionary("OSIRIS"),
    ]

    new_value = json.dumps(instruments_list)
    new_value_compressed = compress_and_hex(new_value)

    ca.caput(pv_address, str(new_value_compressed), True)

    result_compr = ca.caget(pv_address, True)
    result = dehex_and_decompress(result_compr)

    print(result)

    if result != new_value:
        print("Warning! Entered value does not match new value.")
        print("Entered value: " + new_value)
        print("Actual value: " + result)
    else:
        print("Success! The PV now reads: {0}".format(result))
