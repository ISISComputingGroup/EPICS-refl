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
    return compr.encode('hex');


def dehex_and_decompress(value):
    return zlib.decompress(value.decode("hex"))


def set_env():
    epics_ca_addr_list = "EPICS_CA_ADDR_LIST"
    """ If we're not in an EPICS terminal, add the address list to the set of
    environment keys """
    if not epics_ca_addr_list in os.environ.keys():
        os.environ[epics_ca_addr_list] = "127.255.255.255 130.246.51.255"
    print epics_ca_addr_list + " = " + str(os.environ.get(epics_ca_addr_list))

if __name__ == "__main__":
    set_env()

    """ An example address and value. This sets the instrument list """
    pv_address = "CS:INSTLIST"

    instruments_list = [
        {"name": "LARMOR", "hostName": "NDXLARMOR", "pvPrefix": "IN:LARMOR:"},
        {"name": "ALF", "hostName": "NDXALF", "pvPrefix": "IN:ALF:"},
        {"name": "DEMO", "hostName": "NDXDEMO", "pvPrefix": "IN:DEMO:"},
        {"name": "IMAT", "hostName": "NDXIMAT", "pvPrefix": "IN:IMAT:"},
        {"name": "MUONFE", "hostName": "NDEMUONFE", "pvPrefix": "IN:MUONFE:"},
        {"name": "ZOOM", "hostName": "NDXZOOM", "pvPrefix": "IN:ZOOM:"},
        {"name": "IRIS", "hostName": "NDXIRIS", "pvPrefix": "IN:IRIS:"},
    ]

    new_value = json.dumps(instruments_list)
    new_value_compressed = compress_and_hex(new_value)

    ca.caput(pv_address, str(new_value_compressed), True)

    result_compr = ca.caget(pv_address, True)
    result = dehex_and_decompress(result_compr)

    print result
    exit()

    if result != new_value:
        print "Warning! Entered value does not match new value."
        print "Entered value: " + new_value
        print "Actual value: " + result
    else:
        print "Success! The PV was updated to the new value."
