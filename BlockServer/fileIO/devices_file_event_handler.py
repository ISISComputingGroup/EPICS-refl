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

import string
import os

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent

from BlockServer.core.constants import *
from BlockServer.fileIO.base_file_event_handler import BaseFileEventHandler
from server_common.utilities import print_and_log
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.fileIO.schema_checker import ConfigurationIncompleteException, NotConfigFileException
from BlockServer.devices.devices_manager import SCREENS_SCHEMA


class DevicesFileEventHandler(BaseFileEventHandler):
    """ The DevicesFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available device screens as necessary.
    """
    def __init__(self, schema_folder, schema_lock, devices_manager):
        """ Constructor.

        Args:
            schema_folder (string): The location of the schemas
            schema_lock (string): The reentrant lock for the schema
            devices_manager (DevicesManager): The DevicesManager
        """
        super(DevicesFileEventHandler, self).__init__(schema_folder, schema_lock, devices_manager)
        self._schema_filepath = os.path.join(schema_folder, SCREENS_SCHEMA)

    def _update(self, data):
        """
        Updates the device screens with new data.

        Args:
            data (string): The new data as a string of xml
        """
        self._manager.update(data)

    def _check_valid(self, path):
        """
        Check the validity of the device screens file and return the xml data contained within if valid

        Args:
            path (string): The location of the file

        Returns: The device screens data as a string of xml

        """
        extension = path[-4:]
        if extension != ".xml":
            raise NotConfigFileException("File not xml")

        xml_data = self._manager.load_devices(path)

        with self._schema_lock:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(self._schema_filepath, xml_data)

        return xml_data

    def _get_name(self, path):
        """ Not needed for devices. Stub for superclass call """
        return


    def get_modified_message(self, name):
        """
        Returns the log message for a file event.

        Args:
            name (string): Not used for device screens, from superclass call.

        Returns (string): The message

        """
        message = "The device screens file has been modified in the filesystem, ensure it is added to version control"
        return message
