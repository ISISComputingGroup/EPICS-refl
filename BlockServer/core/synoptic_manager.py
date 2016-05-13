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

import os
from server_common.utilities import print_and_log, compress_and_hex, check_pv_name_valid, create_pv_name
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.core.config_list_manager import InvalidDeleteException
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from xml.dom import minidom
from lxml import etree

SYNOPTIC_PRE = "SYNOPTICS:"
SYNOPTIC_GET = ":GET"
SYNOPTIC_SET = ":SET"
SYNOPTIC_SCHEMA = "synoptic.xsd"


class SynopticManager(object):
    """Class for managing the PVs associated with synoptics"""
    def __init__(self, block_server, cas, schema_folder, vc_manager):
        """Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance.
            cas (CAServer): The channel access server for creating PVs on-the-fly
            schema_folder (string): The filepath for the synoptic schema
            vc_manager (ConfigVersionControl): The manager to allow version control modifications
        """
        self._directory = FILEPATH_MANAGER.synoptic_dir
        self._schema_folder = schema_folder
        self._cas = cas
        self._synoptic_pvs = dict()
        self._vc = vc_manager
        self._bs = block_server
        self._default_syn_xml = ""
        self._create_directory()
        self._load_initial()

    def _create_directory(self):
        """If the synoptics directory does not exist then create it"""
        try:
            if not os.path.exists(self._directory):
                os.makedirs(self._directory)
        except Exception as err:
            print_and_log("Error creating synoptic directory: %s" % str(err), "MAJOR")

    def _load_initial(self):
        """Create the PVs for all the synoptics found in the synoptics directory."""
        for f in self._get_synoptic_filenames():
            # Load the data, checking the schema
            try:
                with open(os.path.join(self._directory, f), 'r') as synfile:
                    data = synfile.read()
                    ConfigurationSchemaChecker.check_synoptic_matches_schema(os.path.join(self._schema_folder, SYNOPTIC_SCHEMA),
                                                                             data)
                # Get the synoptic name
                self._create_pv(data)

                self._add_to_version_control(f[0:-4])
            except Exception as err:
                print_and_log("Error creating synoptic PV: %s" % str(err), "MAJOR")

        self._vc.commit("Blockserver started, synoptics updated")

    def _create_pv(self, data):
        """Creates a single PV based on a name and data. Adds this PV to the dictionary returned on get_synoptic_list

        Args:
            data (string): Starting data for the pv, the pv name is derived from the name tag of this
        """
        name = self._get_synoptic_name_from_xml(data)
        if name not in self._synoptic_pvs:
            # Extra check, if a non-case sensitive match exits remove it
            for key in self._synoptic_pvs.keys():
                if name.lower() == key.lower():
                    self._synoptic_pvs.pop(key)
            pv = create_pv_name(name, self._synoptic_pvs.values(), "SYNOPTIC")
            self._synoptic_pvs[name] = pv

        # Create the PV
        self._cas.updatePV(SYNOPTIC_PRE + self._synoptic_pvs[name] + SYNOPTIC_GET, compress_and_hex(data))

    def get_synoptic_list(self):
        """Gets the names and associated pvs of the synoptic files in the synoptics directory.

        Returns:
            list : Alphabetical list of synoptics files on the server, along with their associated pvs
        """
        syn_list = list()
        default_is_none_synoptic = True
        for k, v in self._synoptic_pvs.iteritems():
            if "<name>" + k + "</name>" in self._default_syn_xml:
                syn_list.append({"name": k + " (recommended)", "pv": v, "is_default": True})
                default_is_none_synoptic = False
            else:
                syn_list.append({"name": k, "pv": v, "is_default": False})
        ans = sorted(syn_list, key=lambda x: x['name'].lower())
        # Insert the "blank" synoptic
        ans.insert(0, {"pv": "__BLANK__", "name": "-- NONE --", "is_default": default_is_none_synoptic})
        return ans

    def _get_synoptic_filenames(self):
        """Gets the names of the synoptic files in the synoptics directory. Without the .xml extension.

        Returns:
            list : List of synoptics files on the server
        """
        if not os.path.exists(self._directory):
            print_and_log("Synoptics directory does not exist")
            return list()
        return [f for f in os.listdir(self._directory) if f.endswith(".xml")]

    def set_default_synoptic(self, name):
        """Sets the default synoptic.

        Args:
            name (string): the name of the synoptic to load
        """
        fullname = name + ".xml"
        f = self._get_synoptic_filenames()
        if fullname in f:
            # Load the data
            with open(os.path.join(self._directory, fullname), 'r') as synfile:
                data = synfile.read()
            self._default_syn_xml = data
        else:
            # No synoptic
            self._default_syn_xml = ""

    def get_default_synoptic_xml(self):
        """Gets the XML for the default synoptic.

        Returns:
            string : The XML for the synoptic
        """
        return self._default_syn_xml

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
            xml_data (string): The XML to be saved
        """
        try:
            # Check against schema
            ConfigurationSchemaChecker.check_synoptic_matches_schema(os.path.join(self._schema_folder, SYNOPTIC_SCHEMA),
                                                                     xml_data)
            # Update PVs
            self._create_pv(xml_data)

        except Exception as err:
            print_and_log(err)
            raise

        name = self._get_synoptic_name_from_xml(xml_data)

        save_path = FILEPATH_MANAGER.get_synoptic_path(name)

        # If save file already exists remove first to avoid case issues
        if os.path.exists(save_path):
            os.remove(save_path)

        # Save the data
        with open(save_path, 'w') as synfile:
            pretty_xml = minidom.parseString(xml_data).toprettyxml()
            synfile.write(pretty_xml)

        self._add_to_version_control(name, "%s modified by client" % name)

        self._bs.update_synoptic_monitor()

        print_and_log("Synoptic saved: " + name)

    def _add_to_version_control(self, synoptic_name, commit_message=None):
        # Add to version control
        self._vc.add(FILEPATH_MANAGER.get_synoptic_path(synoptic_name))
        if commit_message is not None:
            self._vc.commit(commit_message)

    def delete_synoptics(self, delete_list):
        """Takes a list of synoptics and removes them from the file system and any relevant PVs.

        Args:
            delete_list (list): The synoptics to delete
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
            self._vc.remove(FILEPATH_MANAGER.get_synoptic_path(synoptic))
        self._vc.commit("Deleted %s" % ', '.join(list(files)))

    def recover_from_version_control(self):
        """A method to revert the configurations directory back to the state held in version control."""
        self._vc.update()

    def update_from_filewatcher(self, name, xml_data):
        """Updates the synoptic list when modifications are made via the filesystem.

        Args:
            name (string):  The name of the synoptic
            xml_data (string): The xml data to update the PV with

        """
        self._add_to_version_control(name, "%s modified on filesystem" % name)

        names = self._synoptic_pvs.keys()
        if name in names:
            self._cas.updatePV(SYNOPTIC_PRE + self._synoptic_pvs[name] + SYNOPTIC_GET, compress_and_hex(xml_data))
        else:
            self._create_pv(xml_data)

        self._bs.update_synoptic_monitor()

    def get_synoptic_schema(self):
        """Gets the XSD data for the synoptic.

        Returns:
            string : The XML for the synoptic schema
        """
        schema = ""
        with open(os.path.join(self._schema_folder, SYNOPTIC_SCHEMA ), 'r') as schemafile:
            schema = schemafile.read()
        return schema

    def get_blank_synoptic(self):
        """Gets a blank synoptic.

        Returns:
            string : The XML for the blank synoptic
        """
        return """<?xml version="1.0" ?><instrument xmlns="http://www.isis.stfc.ac.uk//instrument">
               <name>-- NONE --</name><components/></instrument>"""
