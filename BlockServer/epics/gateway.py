#This file is part of the ISIS IBEX application.
#Copyright (C) 2012-2016 Science & Technology Facilities Council.
#All rights reserved.
#
#This program is distributed in the hope that it will be useful.
#This program and the accompanying materials are made available under the
#terms of the Eclipse Public License v1.0 which accompanies this distribution.
#EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
#AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
#OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
#You should have received a copy of the Eclipse Public License v1.0
#along with this program; if not, you can obtain a copy from
#https://www.eclipse.org/org/documents/epl-v10.php or 
#http://opensource.org/licenses/eclipse-1.0.php

import time
import re
from server_common.channel_access import ChannelAccess
from server_common.utilities import print_and_log


ALIAS_HEADER = """\
##
EVALUATION ORDER ALLOW, DENY

## serve blockserver internal variables, including Flag variables needed by blockserver process to restart gateway
%sCS:GATEWAY:BLOCKSERVER:.*    				    ALLOW	ANYBODY	    1
## allow anybody to generate gateway reports
%sCS:GATEWAY:BLOCKSERVER:report[1-9]Flag		ALLOW	ANYBODY		1
"""

class Gateway(object):
    """A class for interacting with the EPICS gateway that creates the aliases used for implementing blocks"""

    def __init__(self, prefix, block_prefix, pvlist_file, pv_prefix):
        """Constructor.

        Args:
            prefix (string): The prefix for the gateway
            block_prefix (string): The block prefix
            pvlist_file (string): Where to write the gateway file
            pv_prefix (string): Prefix for instrument PVs
        """
        self._prefix = prefix
        self._block_prefix = block_prefix
        self._pvlist_file = pvlist_file
        self._pv_prefix = pv_prefix

    def exists(self):
        """Checks the gateway exists by querying on of the PVs.

        Returns:
            bool : Whether the gateway is running and is accessible
        """
        val = ChannelAccess.caget(self._prefix + "pvtotal")
        if val is None:
            return False
        else:
            return True

    def _reload(self):
        print_and_log("Reloading gateway")
        try:
            # Have to wait after put as the gateway does not do completion callbacks (it is not an IOC)
            ChannelAccess.caput(self._prefix + "newAsFlag", 1)

            while ChannelAccess.caget(self._prefix + "newAsFlag") == 1:
                time.sleep(0.01)
            print_and_log("Gateway reloaded")
        except Exception as err:
            print_and_log("Problem with reloading the gateway {}".format(err))

    def _generate_alias_file(self, blocks=None):
        # Generate blocks.pvlist for gateway
        with open(self._pvlist_file, 'w') as f:
            header = ALIAS_HEADER % (self._pv_prefix, self._pv_prefix)
            f.write(header)
            if blocks is not None:
                for name, value in blocks.iteritems():
                    lines = self._generate_alias(value.name, value.pv, value.local)
                    for l in lines:
                        f.write(l)
            # Add a blank line at the end!
            f.write("\n")

    def _generate_alias(self, blockname, pv, local):
        print_and_log("Creating block: {} for {}".format(blockname, self._pv_prefix + pv if local else + pv))
        lines = list()
        if pv.endswith(".VAL"):
            # Strip off the .VAL
            pv = pv.rstrip(".VAL")
        # look for a field name in PV
        m = re.match(r'.*(\.[A-Z0-9]+)$', pv)
        if m:
            pvsuffix = m.group(1)
        else:
            pvsuffix = None
        if pv.endswith(":SP"):
            # The block points at a setpoint
            lines.append("## The block points at a :SP, so it needs an optional group as genie_python will append an additional :SP, but ignore :RC:\n")
            if local:
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\(:SP\)?\([.:].*\)    ALIAS    %s%s\\2\n' % (self._pv_prefix, self._block_prefix,
                                                                                 blockname, self._pv_prefix, pv))
                lines.append('%s%s%s\(:SP\)?:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s\(:SP\)?    ALIAS    %s%s\n' %
                             (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\(:SP\)?\([.:].*\)    ALIAS    %s\\2\n' % (self._pv_prefix, self._block_prefix,
                                                                               blockname, pv))
                lines.append('%s%s%s\(:SP\)?:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s\(:SP\)?    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
        elif pvsuffix is not None:
            # The block points at a readback value (most likely for a motor)
            lines.append("## The block points at a %s field, so it needs entries for both reading the field and for the rest, but ignore :RC:\n" % (pvsuffix))
            if local:
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s%s\\1\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                                         self._pv_prefix, pv.rstrip(pvsuffix)))
                lines.append('%s%s%s:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s[.]VAL    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                                  self._pv_prefix, pv))
                lines.append('%s%s%s    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                            self._pv_prefix, pv))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s\\1\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                                       pv.rstrip(pvsuffix)))
                lines.append('%s%s%s:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s[.]VAL    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
                lines.append('%s%s%s    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
        else:
            # Standard case
            lines.append("## Standard block with entries for matching :SP and :SP:RBV as well as .EGU, but ignore :RC:\n")
            if local:
                # Pattern match is for picking up any any SP or SP:RBV
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s%s\\1\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                                         self._pv_prefix, pv))
                lines.append('%s%s%s:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                            self._pv_prefix, pv))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any any SP or SP:RBV
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s\\1\n' % (self._pv_prefix, self._block_prefix, blockname,
                                                                       pv))
                lines.append('%s%s%s:RC:.*    DENY\n' % (self._pv_prefix, self._block_prefix, blockname))
                lines.append('%s%s%s    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
        return lines

    def set_new_aliases(self, blocks):
        """Creates the aliases for the blocks and restarts the gateway.

        Args:
            blocks (OrderedDict): The blocks that belong to the configuration
        """
        self._generate_alias_file(blocks)
        self._reload()
