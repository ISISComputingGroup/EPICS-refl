import os
from server_common.utilities import print_and_log, compress_and_hex, check_pv_name_valid, create_pv_name
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.core.config_list_manager import InvalidDeleteException
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from lxml import etree

SYNOPTIC_PRE = "SYNOPTICS:"
SYNOPTIC_GET = ":GET"
SYNOPTIC_SET = ":SET"


class SynopticManager(object):
    """Class for managing the PVs associated with synoptics"""
    def __init__(self, synoptic_folder, cas, schema_folder, vc_manager):
        """Constructor.

        Args:
            synoptic_folder (string) : The filepath where synoptics are stored
            cas (CAServer) : The channel access server for creating PVs on-the-fly
            schema_folder (string) : The filepath for the synoptic schema
            vc_manager (ConfigVersionControl) : The manager to allow version control modifications
        """
        self._directory = os.path.abspath(synoptic_folder)
        self._schema_folder = schema_folder
        self._cas = cas
        self._synoptic_pvs = dict()
        self._vc = vc_manager
        self.create_pvs()

    def create_pvs(self):
        """Create the PVs for all the synoptics found in the synoptics directory."""
        for f in self._get_synoptic_filenames():
            # Load the data, checking the schema
            with open(os.path.join(self._directory, f + ".xml"), 'r') as synfile:
                data = synfile.read()
                ConfigurationSchemaChecker.check_synoptic_matches_schema(self._schema_folder, data)
            # Get the synoptic name
            self._create_pv(f, data)

    def _create_pv(self, name, data):
        pv = create_pv_name(name, self._synoptic_pvs.values(), "SYNOPTIC")
        self._synoptic_pvs[name] = pv

        # Create the PV
        self._cas.updatePV(SYNOPTIC_PRE + pv + SYNOPTIC_GET, compress_and_hex(data))

    def get_synoptic_list(self):
        """Gets the names and associated pvs of the synoptic files in the synoptics directory.

        Returns:
            list : List of synoptics files on the server, along with their associated pvs
        """
        syn_list = list()
        for k, v in self._synoptic_pvs.iteritems():
            syn_list.append({"name": k, "pv": v})
        return syn_list

    def _get_synoptic_filenames(self):
        """Gets the names of the synoptic files in the synoptics directory. Without the .xml extension.

        Returns:
            list : List of synoptics files on the server
        """
        if not os.path.exists(self._directory):
            print_and_log("Synoptics directory does not exist")
            return list()
        return [f[0:-4] for f in os.listdir(self._directory) if f.endswith(".xml")]

    def get_default_synoptic_xml(self):
        """Gets the XML for the default synoptic.

        Returns:
            string : The XML for the synoptic
        """
        # TODO: Default is first synoptic for now
        f = self._get_synoptic_filenames()
        if len(f) > 0:
            # Load the data
            with open(os.path.join(self._directory, f[0] + ".xml"), 'r') as synfile:
                data = synfile.read()
            return data
        else:
            # No synoptic
            return ""

    def _get_synoptic_name_from_xml(self, xml_data):
        name = None
        root = etree.fromstring(xml_data)
        for child in root:
            if child.tag.split('}', 1)[1] == "name":
                name = child.text
        if name is None:
            raise Exception("Synoptic contains no name tag")
        return name

    def save_synoptic_xml(self, xml_data):
        """Saves the xml under the filename taken from the xml name tag.

        Args:
            xml_data (string) : The XML to be saved
        """
        try:
            # Check against schema
            ConfigurationSchemaChecker.check_synoptic_matches_schema(self._schema_folder, xml_data)

            name = self._get_synoptic_name_from_xml(xml_data)

            self._create_pv(name, xml_data)

            self._vc.add(self._schema_folder + "\\" + name)
            self._vc.commit("%s modified by client" % name)
        except Exception as err:
            print_and_log(err)
            raise

        # Save the data
        with open(os.path.join(self._directory, name + ".xml"), 'w') as synfile:
            synfile.write(xml_data)

    def delete_synoptics(self, delete_list):
        """Takes a list of synoptics and removes them from the file system and any relevant PVs.

        Args:
            delete_list (list) : The synoptics to delete
        """
        print_and_log("Deleting: " + ', '.join(list(delete_list)), "INFO")
        delete_list = set(delete_list)
        if not delete_list.issubset(self._synoptic_pvs.keys()):
            raise InvalidDeleteException("Delete list contains unknown configurations")
        for synoptic in delete_list:
            self._cas.deletePV(SYNOPTIC_PRE + self._synoptic_pvs[synoptic] + SYNOPTIC_GET)
            del self._synoptic_pvs[synoptic]
        self._update_version_control_post_delete(delete_list)  # Git is case sensitive

    def _update_version_control_post_delete(self, files):
        for synoptic in files:
            self._vc.remove(os.path.join(self._directory, synoptic + ".xml"))
        self._vc.commit("Deleted %s" % ', '.join(list(files)))