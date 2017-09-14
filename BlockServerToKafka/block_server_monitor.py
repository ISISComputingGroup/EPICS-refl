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
from CaChannel import CaChannel
from CaChannel import CaChannelException
from server_common import utilities
import ca
import json
from BlockServer.core.macros import BLOCK_PREFIX


class BlockServerMonitor:
    def __init__(self, address, pvprefix, producer):
        self.PVPREFIX = pvprefix
        self.address = address
        self.channel = CaChannel()
        self.producer = producer
        self.last_pv = []
        try:
            self.channel.searchw(self.address)
        except CaChannelException:
            print ("Unable to find pv " + self.address)
            return

        # Create the CA monitor callback
        self.channel.add_masked_array_event(
            ca.dbf_type_to_DBR_STS(self.channel.field_type()),
            0,
            ca.DBE_VALUE,
            self.update,
            None)
        self.channel.pend_event()

    def block_name_to_pv_name(self, blk):
        return '{}{}{}'.format(self.PVPREFIX, BLOCK_PREFIX, blk.upper())

    def update(self, epics_args, user_args):
        data = str(bytearray(epics_args['pv_value'])).replace("\x00", "")
        data = utilities.dehex_and_decompress(data)
        blocks = json.loads(data)

        pvs = [self.block_name_to_pv_name(blk) for blk in blocks]
        if pvs != self.last_pv:
            print("Configuration changed to: {}".format(pvs))
            self.producer.remove_config(self.last_pv)
            self.producer.add_config(pvs)
            self.last_pv = pvs