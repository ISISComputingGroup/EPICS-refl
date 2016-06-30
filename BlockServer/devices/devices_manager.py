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
from server_common.utilities import print_and_log, compress_and_hex
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema
from BlockServer.core.constants import FILENAME_SCREENS as SCREENS_FILE
from BlockServer.core.pv_names import BlockserverPVNames
from BlockServer.core.on_the_fly_pv_interface import OnTheFlyPvInterface
from xml.dom import minidom


SCREENS_SCHEMA = "screens.xsd"
GET_SCREENS = BlockserverPVNames.prepend_blockserver('GET_SCREENS')
SET_SCREENS = BlockserverPVNames.prepend_blockserver('SET_SCREENS')


class DevicesManager(OnTheFlyPvInterface):
    """Class for managing the PVs associated with devices"""
    def __init__(self, block_server, schema_folder, vc_manager, active_configholder):
        """Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance
            schema_folder (string): The filepath for the devices schema
            vc_manager (ConfigVersionControl): The manager to allow version control modifications
            active_configholder (ActiveConfigHolder): A reference to the active configuration
        """
        self._pvs_to_set = [SET_SCREENS]
        self._schema_folder = schema_folder
        self._devices_pvs = dict()
        self._vc = vc_manager
        self._bs = block_server
        self._activech = active_configholder
        self._current_config = ""
        self._data = ""
        self._create_standard_pvs()

    def _create_standard_pvs(self):
        self._bs.add_string_pv_to_db(GET_SCREENS, 16000)
        self._bs.add_string_pv_to_db(SET_SCREENS, 16000)

    def read_pv_exists(self, pv):
        # Reads are handled by the monitors
        return False

    def write_pv_exists(self, pv):
        return pv in self._pvs_to_set

    def handle_pv_write(self, pv, data):
        if pv == SET_SCREENS:
            self.save_devices_xml(data)
            self.update_monitors()

    def handle_pv_read(self, pv):
        # Nothing to do as it is all handled by monitors
        pass

    def update_monitors(self):
        with self._bs.monitor_lock:
            print "UPDATING DEVICES MONITORS"
            self._bs.setParam(GET_SCREENS, compress_and_hex(self._data))
            self._bs.updatePVs()

    def initialise(self, full_init=False):
        # Get the config name
        name = self._activech.get_config_name()
        self._set_current_config_name(name)
        self._load_current()
        self.update_monitors()

    def _load_current(self):
        """Create the PVs for all the devices found in the devices directory."""

        devices_file_name = None
        try:
            devices_file_name = self.get_devices_filename()
            with open(devices_file_name, 'r') as devfile:
                self._data = devfile.read()
        except IOError as err:
            self._data = self.get_blank_devices()
            print_and_log("Unable to load devices file. %s. The PV data will default to a blank set of devices." % err,
                          "MINOR")

        try:
            ConfigurationSchemaChecker.check_xml_matches_schema(
                os.path.join(self._schema_folder, SCREENS_SCHEMA),
                self._data, "Screens")
        except ConfigurationInvalidUnderSchema as err:
            print_and_log(err)

        if devices_file_name is not None:
            try:
                self._add_to_version_control("New change found in devices file %s" % self._current_config)
            except Exception as err:
                print_and_log("Unable to add new data to version control. " + str(err), "MINOR")

        self._vc.commit("Blockserver started, devices updated")

    def get_devices_filename(self):
        """Gets the names of the devices files in the devices directory. Without the .xml extension.

        Returns:
            string : Current devices file name. Returns empty string if the file does not exist.
        """
        if not os.path.exists(self._current_config):
            raise IOError("Current devices file %s does not exist" % self._current_config)
        return self._current_config

    def _set_current_config_name(self, current_config_name):
        """Sets the names of the current configuration file.

        Args:
            current_config_name (string): The name of the current configuration file.
        """
        self._current_config = os.path.join(FILEPATH_MANAGER.get_config_path(current_config_name)
                                            , SCREENS_FILE)

        print_and_log("Devices configuration file set to %s" % self._current_config)

    def save_devices_xml(self, xml_data):
        """Saves the xml in the current "screens.xml" config file.

        Args:
            xml_data (string): The XML to be saved
        """
        try:
            # Check against schema
            ConfigurationSchemaChecker.check_xml_matches_schema(os.path.join(self._schema_folder, SCREENS_SCHEMA),
                                                                xml_data,"Screens")
            # Update PVs
            self.update_monitors()

        except Exception as err:
            print_and_log(err)
            raise

        save_path = self._current_config

        # If save file already exists remove first to avoid case issues
        if os.path.exists(save_path):
            os.remove(save_path)

        # Save the data
        with open(save_path, 'w') as devfile:
            pretty_xml = minidom.parseString(xml_data).toprettyxml()
            devfile.write(pretty_xml)

        self._add_to_version_control("%s modified by client" % self._current_config)

        print_and_log("Devices saved to %s" % self._current_config)

    def _add_to_version_control(self, commit_message=None):
        # Add to version control
        self._vc.add(self._current_config)
        if commit_message is not None:
            self._vc.commit(commit_message)

    def get_blank_devices(self):
        """Gets a blank devices xml

                Returns:
                    string : The XML for the blank devices set
                """
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
                </devices>"""
