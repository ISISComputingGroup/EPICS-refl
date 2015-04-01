import os
from server_common.utilities import print_and_log, compress_and_hex
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker

SYNOPTIC_PRE = "SYNOPTICS:"
SYNOPTIC_GET = ":GET"
SYNOPTIC_SET = ":SET"


class SynopticManager(object):
    """Class for managing the PVs associated with synoptics"""
    def __init__(self, synoptic_folder, cas, schema_folder):
        """Constructor.

        Args:
            synoptic_folder (string) : The filepath where synoptics are stored
            cas (CAServer) : The channel access server for creating PVs on-the-fly
            schema_folder (string) : The filepath for the synoptic schema
        """
        self._directory = os.path.abspath(synoptic_folder)
        self._schema_folder = schema_folder
        self._cas = cas
        self._current = None

    def create_pvs(self):
        """Create the PVs for all the synoptics found in the synoptics directory."""
        for f in self.get_synoptic_filenames():
            # Load the data, checking the schema
            with open(os.path.join(self._directory, f), 'r') as synfile:
                data = synfile.read()
                ConfigurationSchemaChecker.check_synoptic_matches_schema(self._schema_folder, data)
            # Get the synoptic name
            name = f[0:-4].upper()
            # Create the PV
            self._cas.updatePV(SYNOPTIC_PRE + name + SYNOPTIC_GET, compress_and_hex(data))

    def get_synoptic_filenames(self):
        """Gets the names of the synoptic files in the synoptics directory.

        Returns:
            (list) : List of synoptics files on the server
        """
        if not os.path.exists(self._directory):
            print_and_log("Synoptics directory does not exist")
            return list()
        return [f for f in os.listdir(self._directory) if f.endswith(".xml")]

    def get_current_synoptic_xml(self):
        """Gets the XML for the current synoptic.

        Returns:
            (string) : The XML for the synoptic
        """
        # TODO: for now we just return the first synoptic in the directory but in the future we will need to set the
        # current synoptic
        f = self.get_synoptic_filenames()
        if len(f) > 0:
            # Load the data
            with open(os.path.join(self._directory, f[0]), 'r') as synfile:
                data = synfile.read()
            return data
        else:
            # No synoptic
            return ""

    def set_current_synoptic_xml(self, xml_data):
        """Sets the XML for the current synoptic.

        Args:
            xml_data (string) : The XML to be saved
        """
        # TODO: for now we just modify the first synoptic in the directory but in the future we will need to modify the
        # current synoptic

        # Check against schema
        try:
            ConfigurationSchemaChecker.check_synoptic_matches_schema(self._schema_folder, xml_data)
        except Exception as err:
            print_and_log(err)
            raise

        f = self.get_synoptic_filenames()
        if len(f) > 0:
            # Load the data
            with open(os.path.join(self._directory, f[0]), 'w') as synfile:
                synfile.write(xml_data)
