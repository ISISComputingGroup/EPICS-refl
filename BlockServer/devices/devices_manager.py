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
from server_common.common_exceptions import MaxAttemptsExceededException
from server_common.utilities import print_and_log, compress_and_hex
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker, ConfigurationInvalidUnderSchema
from BlockServer.core.constants import FILENAME_SCREENS as SCREENS_FILE
from server_common.pv_names import BlockserverPVNames
from BlockServer.core.on_the_fly_pv_interface import OnTheFlyPvInterface
from BlockServer.devices.devices_file_io import DevicesFileIO

SCREENS_SCHEMA = "screens.xsd"
GET_SCREENS = BlockserverPVNames.GET_SCREENS
SET_SCREENS = BlockserverPVNames.SET_SCREENS
GET_SCHEMA = BlockserverPVNames.SCREENS_SCHEMA


class DevicesManager(OnTheFlyPvInterface):
    """ Class for managing the PVs associated with devices"""
    def __init__(self, block_server, schema_folder, file_io=DevicesFileIO()):
        """ Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance
            schema_folder (string): The filepath for the devices schema
            file_io (DevicesFileIO): Object used for loading and saving files
        """
        super(DevicesManager, self).__init__()
        self._file_io = file_io
        self.pvs_to_write.append(SET_SCREENS)
        self._schema_folder = schema_folder
        self._schema = ""
        self._devices_pvs = dict()
        self._bs = block_server
        self._data = ""
        self._create_standard_pvs()
        self._load_current()
        self.update_monitors()

    def _create_standard_pvs(self):
        """ Creates new PVs holding information relevant to the device screens. """
        self._bs.add_string_pv_to_db(GET_SCREENS, 16000)
        self._bs.add_string_pv_to_db(SET_SCREENS, 16000)
        self._bs.add_string_pv_to_db(GET_SCHEMA, 16000)

    def handle_pv_write(self, pv, data):
        if pv == SET_SCREENS:
            try:
                self.save_devices_xml(data)
                self.update_monitors()
            except IOError as err:
                print_and_log("Could not save device screens: {error} "
                              "The PV data will not be updated.".format(error=err), "MINOR")

    def handle_pv_read(self, pv):
        # Nothing to do as it is all handled by monitors
        pass

    def update_monitors(self):
        """ Writes new device screens data to PVs """
        with self._bs.monitor_lock:
            print_and_log("Updating devices monitors")
            self._bs.setParam(GET_SCHEMA, compress_and_hex(self.get_devices_schema()))
            self._bs.setParam(GET_SCREENS, compress_and_hex(self._data))
            self._bs.updatePVs()

    def on_config_change(self, full_init=False):
        # Devices don't need to change with config
        pass

    def _load_current(self):
        """ Gets the devices XML for the current instrument"""
        # Read the data from file
        try:
            self._data = self._file_io.load_devices_file(self.get_devices_filename())
        except (MaxAttemptsExceededException, IOError):
            self._data = self.get_blank_devices()
            print_and_log("Unable to load devices file. Please check the file is not in use by another process. "
                          "The PV data will default to a blank set of devices.", "MINOR")
            return

        try:
            # Check against the schema
            ConfigurationSchemaChecker.check_xml_data_matches_schema(os.path.join(self._schema_folder,
                                                                                  SCREENS_SCHEMA), self._data)
        except ConfigurationInvalidUnderSchema as err:
            self._data = self.get_blank_devices()
            print_and_log(err.message)
            return

    def get_devices_filename(self):
        """ Gets the names of the devices files in the devices directory.

        Returns:
            string : Current devices file name
        """

        return os.path.join(FILEPATH_MANAGER.devices_dir, SCREENS_FILE)

    def update(self, xml_data, message=None):
        """ Updates the current device screens with new data.

        Args:
            xml_data: The updated device screens data
            message: The commit message

        Returns:

        """
        self._data = xml_data
        self.update_monitors()

    def save_devices_xml(self, xml_data):
        """ Saves the xml in the current "screens.xml" config file.

        Args:
            xml_data (string): The XML to be saved
        """
        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(os.path.join(self._schema_folder, SCREENS_SCHEMA),
                                                                     xml_data)
        except ConfigurationInvalidUnderSchema as err:
            print_and_log(err.message)
            return

        try:
            if not os.path.exists(FILEPATH_MANAGER.devices_dir):
                os.makedirs(FILEPATH_MANAGER.devices_dir)
            self._file_io.save_devices_file(self.get_devices_filename(), xml_data)
        except MaxAttemptsExceededException:
            raise IOError("Unable to save devices file. Please check the file is not in use by another process.")

        # Update PVs
        self.update(xml_data, "Device screens modified by client")
        print_and_log("Devices saved to " + self.get_devices_filename())

    def get_devices_schema(self):
        """ Gets the XSD data for the devices screens.

        Note: Only reads file once, if the file changes then the BlockServer will need to be restarted

        Returns:
            string : The XML for the devices screens schema
        """
        if self._schema == "":
            # Try loading it
            with open(os.path.join(self._schema_folder, SCREENS_SCHEMA), 'r') as schemafile:
                self._schema = schemafile.read()
        return self._schema

    def get_blank_devices(self):
        """ Gets a blank devices xml

        Returns:
            string : The XML for the blank devices set
        """
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <devices xmlns="http://epics.isis.rl.ac.uk/schema/screens/1.0/">
                </devices>"""

    def load_devices(self, path):
        """
        Reads device screens data from an xml file at a specified location

        Args:
            path (string): The location of the xml devices file

        Returns: the xml data

        """
        with open(path, 'r') as synfile:
            xml_data = synfile.read()

        return xml_data
