import time
from server_common.channel_access import caget, caput
from server_common.utilities import print_and_log

class Gateway(object):
    """A class for interacting with the EPICS gateway that creates the aliases used for implementing blocks"""

    def __init__(self, prefix, block_prefix, pvlist_file, pv_prefix):
        """Constructor.

        Args:
            prefix (string) : The prefix for the gateway
            block_prefix (string) : The block prefix
            pvlist_file (string) : Where to write the gateway file
            pv_prefix (string) : Prefix for instrument PVs
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
        val = caget(self._prefix + "pvtotal")
        if val is None:
            return False
        else:
            return True

    def _reload(self):
        print_and_log("Reloading gateway")
        try:
            # Have to wait after put as the gateway does not do completion callbacks (it is not an IOC)
            caput(self._prefix + "newAsFlag", 1, False)
            while(caget(self._prefix + "newAsFlag") == 1) :
                time.sleep(1)
            print_and_log("Gateway reloaded")
        except Exception as err:
            print_and_log("Problem with reloading the gateway %s" % err)

    def _generate_alias_file(self, blocks=None):
        # Generate blocks.pvlist for gateway
        f = open(self._pvlist_file, 'w')
        header = """\
## Make ALLOW rules override DENY rules
EVALUATION ORDER DENY, ALLOW
## serve nothing by default, this is to avoid gateway loops
.*												DENY
## serve blockserver internal variables, including Flag variables needed by blockserver process to restart gateway
%sCS:GATEWAY:BLOCKSERVER:.*    				    ALLOW	ANYBODY	    1
## allow anybody to generate gateway reports 
%sCS:GATEWAY:BLOCKSERVER:report[1-9]Flag		ALLOW	ANYBODY		1
""" % ( self._pv_prefix, self._pv_prefix )
        f.write(header)
        if blocks is not None:
            for name, value in blocks.iteritems():
                lines = self._generate_alias(value.name, value.pv, value.local)
                for l in lines:
                    f.write(l)
        # Add a blank line at the end!
        f.write("\n")
        f.close()

    def _generate_alias(self, blockname, pv, local):
        print("Creating block: %s for %s" % (blockname, pv))
        lines = list()
        if pv.endswith(".VAL"):
            # Strip off the .VAL
            pv = pv.rstrip(".VAL")
        if pv.endswith(":SP"):
            # The block points at a setpoint
            lines.append("## The block points at a :SP, so it needs an optional group as genie_python will append an additional :SP\n")
            if local:
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\(:SP\)?    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
                lines.append('%s%s%s\(:SP\)?\([.:].*\)    ALIAS    %s%s\\2\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s\(:SP\)?    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
                lines.append('%s%s%s\(:SP\)?\([.:].*\)    ALIAS    %s\\2\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
        elif pv.endswith(".RBV"):
            # The block points at a readback value (most likely for a motor)
            lines.append("## The block points at a .RBV, so it needs entries for both reading the RBV and for the rest\n")
            if local:
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s%s\\1\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv.rstrip(".RBV")))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any extras like :RBV or .EGU
                lines.append('%s%s%s    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s\\1\n' % (self._pv_prefix, self._block_prefix, blockname, pv.rstrip(".RBV")))
        else:
            # Standard case
            lines.append("## Standard block with entries for matching :SP and :SP:RBV as well as .EGU\n")
            if local:
                # Pattern match is for picking up any any SP or SP:RBV
                lines.append('%s%s%s    ALIAS    %s%s\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s%s\\1\n' % (self._pv_prefix, self._block_prefix, blockname, self._pv_prefix, pv))
            else:
                # pv_prefix is hard-coded for non-local PVs
                # Pattern match is for picking up any any SP or SP:RBV
                lines.append('%s%s%s    ALIAS    %s\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
                lines.append('%s%s%s\([.:].*\)    ALIAS    %s\\1\n' % (self._pv_prefix, self._block_prefix, blockname, pv))
        return lines

    def set_new_aliases(self, blocks):
        """Creates the aliases for the blocks and restarts the gateway.

        Args:
            blocks (OrderedDict) : The blocks that belong to the configuration
        """
        self._generate_alias_file(blocks)
        self._reload()