import time
from server_common.channel_access import caget, caput
from server_common.utilities import print_and_log


class Gateway(object):
    """A class for interacting with the EPICS gateway that creates the aliases used for implementing blocks"""

    def __init__(self, prefix, block_prefix, pvlist_file):
        """Constructor.

        Args:
            prefix (string) : The prefix for the gateway
            block_prefix (string) : The block prefix
            pvlist_file (string) : Where to write the gateway file
        """
        self._prefix = prefix
        self._block_prefix = block_prefix
        self._pvlist_file = pvlist_file

    def exists(self):
        """Checks the gateway exists by querying on of the PVs.

        Returns:
            bool : Whether the gateway is running and is accessible
        """
        val = caget(self._prefix + "pvtotal")
        if val is None:
            return False
        else:
            return True

    def _restart(self):
        print_and_log("Restarting gateway")
        try:
            # Have to wait after put as the gateway does not do completion callbacks (it is not an IOC)
            caput(self._prefix + "newAsFlag", 1, False)
            time.sleep(1)
            print_and_log("Gateway restarted")
        except Exception as err:
            print_and_log("Problem with restarting the gateway %s" % err)

    def _generate_alias_file(self, blocks=None):
        # Generate blocks.pvlist for gateway
        f = open(self._pvlist_file, 'w')
        if blocks is not None:
            for name, value in blocks.iteritems():
                lines = self._generate_alias(value.name, value.pv, value.local)
                for l in lines:
                    f.write(l)
        # Allow the gateway diagnostic PVs through
        # f.write(self._gateway_prefix + '.* ALLOW \n')
        f.write('.*:CS:GATEWAY:.*    ALLOW\n')
        # Add a blank line at the end!
        f.write("\n")
        f.close()

    def _generate_alias(self, blockname, pv, local):
        print("Creating block: %s for %s" % (blockname, pv))
        if pv.endswith(".VAL"):
            # Strip off the .VAL
            pv = pv.rstrip(".VAL")
        if pv.endswith(":SP"):
            # The block points at a setpoint
            lines = list()
            lines.append("# The block points at a :SP, so it needs an optional group as genie_python will append an additional :SP\n")
            if local:
                # First pattern match is used for getting the prefix (e.g. MYPVPREFIX)
                # The 2nd is for picking up any extras like :RBV or .EGU
                lines.append('\(.*\)%s%s\(:SP\)?\(.*\)    ALIAS    \\1%s\\3\n' % (self._block_prefix, blockname, pv))
                return lines
            else:
                # First pattern match is ignored as the prefix is hard-coded for non-local PVs
                # The 2nd is for picking up any extras like :RBV or .EGU
                lines.append('\(.*\)%s%s\(:SP\)?\(.*\)    ALIAS    %s\\3\n' % (self._block_prefix, blockname, pv))
                return lines
        elif pv.endswith(".RBV"):
            # The block points at a readback value (most likely for a motor)
            lines = list()
            lines.append("# The block points at a .RBV, so it needs two entries one for reading the RBV and one for the rest\n")
            if local:
                # First pattern match is used for getting the prefix (e.g. MYPVPREFIX)
                # The 2nd is for picking up any extras like .EGU
                lines.append('\(.*\)%s%s    ALIAS    \\1%s\n' % (self._block_prefix, blockname, pv))
                lines.append('\(.*\)%s%s\(.+\)    ALIAS    \\1%s\\2\n' % (self._block_prefix, blockname,
                                                                          pv.rstrip(".RBV")))
                return lines
            else:
                # First pattern match is ignored as the prefix is hard-coded for non-local PVs
                # The 2nd is for picking up any extras like :RBV or .EGU
                lines.append('\(.*\)%s%s    ALIAS    %s\n' % (self._block_prefix, blockname, pv))
                lines.append('\(.*\)%s%s\(.+\)    ALIAS    %s\\2\n' % (self._block_prefix, blockname,
                                                                       pv.rstrip(".RBV")))
                return lines
        else:
            # Standard case
            if local:
                # First pattern match is used for getting the prefix (e.g. MYPVPREFIX)
                # The 2nd is for picking up any SP or SP:RBV
                return ['\(.*\)%s%s\(.*\)    ALIAS    \\1%s\\2\n' % (self._block_prefix, blockname, pv)]
            else:
                # First pattern match is ignored as the prefix is hard-coded for non-local PVs
                # The 2nd is for picking up any SP or SP:RBV
                return ['\(.*\)%s%s\(.*\)    ALIAS    %s\\2\n' % (self._block_prefix, blockname, pv)]

    def set_new_aliases(self, blocks):
        """Creates the aliases for the blocks and restarts the gateway.

        Args:
            blocks (OrderedDict) : The blocks that belong to the configuration
        """
        self._generate_alias_file(blocks)
        self._restart()