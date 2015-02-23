import os
from BlockServer.config.constants import SYNOPTIC_DIRECTORY
from server_common.utilities import print_and_log, compress_and_hex

SYNOPTIC_GET_PV = ":GET_SYNOPTIC"
SYNOPTIC_SET_PV = ":SET_SYNOPTIC"


class SynopticManager(object):
    """Class for managing the PVs associated with synoptics"""
    def __init__(self, config_folder, cas):
        self.directory = os.path.abspath(config_folder + SYNOPTIC_DIRECTORY)
        self.cas = cas

    def create_pvs(self):
        """Create the PVs for all the synoptics found in the synoptics directory"""
        if not os.path.exists(self.directory):
            raise Exception("Synoptics directory does not exist")
        for f in os.listdir(self.directory):
            if f.endswith(".xml"):
                # Load the data
                with open(os.path.join(self.directory, f), 'r') as synfile:
                    data = synfile.read()
                # Get the synoptic name
                name = f[0:-4].upper()
                # Create the PV
                self.cas.updatePV(name + SYNOPTIC_GET_PV, compress_and_hex(data))

