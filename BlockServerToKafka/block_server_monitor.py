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
from server_common.utilities import dehex_and_decompress, print_and_log
import ca
import json
from BlockServer.core.macros import BLOCK_PREFIX


class BlockServerMonitor:
    """ Class that monitors the blockserver to see when the config has changed.
    """
    def __init__(self, address, pvprefix, producer):
        self.PVPREFIX = pvprefix
        self.address = address
        self.channel = CaChannel()
        self.producer = producer
        self.last_pvs = []
        try:
            self.channel.searchw(self.address)
        except CaChannelException:
            print_and_log("Unable to find pv {}".format(self.address))
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
        """ Converts a block name to a PV name by adding the prefixes.
        Args:
            blk (string): the name of the block
        Returns:
            (string) the associated PV name
        """
        return '{}{}{}'.format(self.PVPREFIX, BLOCK_PREFIX, blk.upper())

    def convert_to_string(self, pv_array):
        """ Converts from byte array to string and removes null characters
        Args:
            pv_array(bytearray): The byte array of PVs.
        Returns:
            (string) The string formed from the bytearray
        """
        # Cannot get the number of elements in the array so just convert to bytes and remove the nulls
        return str(bytearray(pv_array)).replace("\x00", "")

    def update_config(self, blocks):
        """ Updates the forwarder configuration to monitor the supplied blocks
        Args:
            blocks(list): Blocks in the BlockServer containing PV data
        """
        pvs = [self.block_name_to_pv_name(blk) for blk in blocks]
        if pvs != self.last_pvs:
            print_and_log("Configuration changed to: {}".format(pvs))
            self.producer.remove_config(self.last_pvs)
            self.producer.add_config(pvs)
            self.last_pvs = pvs

    def update(self, epics_args, user_args):
        """ Updates the kafka config when the blockserver changes. This is called from the monitor.
        Args:
            epics_args(dict): Dictionary containing the information for the blockserver blocks PV.
            user_args(dict): not used.
        """
        data = self.convert_to_string(epics_args['pv_value'])
        data = dehex_and_decompress(data)
        blocks = json.loads(data)

        self.update_config(blocks)
