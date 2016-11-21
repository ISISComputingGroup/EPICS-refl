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
from server_common.utilities import print_and_log
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.fileIO.schema_checker import ConfigurationIncompleteException, NotConfigFileException
from BlockServer.devices.devices_manager import SCREENS_SCHEMA


class DevicesFileEventHandler(FileSystemEventHandler):
    """ The DevicesFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available device screens as necessary.
    """
    def __init__(self, schema_folder, schema_lock, devices_manager):
        """Constructor.

        Args:
            schema_folder (string): The location of the schemas
            schema_lock (string): The reentrant lock for the schema
            devices_manager (DevicesManager): The DevicesManager
        """
        self._schema_filepath = os.path.join(schema_folder, SCREENS_SCHEMA)
        self._schema_lock = schema_lock
        self._devices_manager = devices_manager

    def on_any_event(self, event):
        """Catch-all event handler.

        Args:
            event (FileSystemEvent): The event object representing the file system event
        """
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    if type(event) is FileMovedEvent:
                        modified_path = event.dest_path
                    else:
                        modified_path = event.src_path

                    devices = self._check_devices_valid(modified_path)

                    # Update
                    self._devices_manager.update(devices, "Device screens modified on filesystem")

                    # Inform user
                    print_and_log("The device screens list has been modified in the filesystem, ensure it is added to "
                                  "version control", "INFO", "FILEWTCHR")

                except NotConfigFileException as err:
                    print_and_log("File Watcher1: " + repr(err), src="FILEWTCHR")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher2: " + repr(err), src="FILEWTCHR")
                except Exception as err:
                    print_and_log("File Watcher3: " + repr(err), "MAJOR", "FILEWTCHR")

    def on_deleted(self, event):
        """"Called when a file or directory is deleted.

        Args:
            event (DirDeletedEvent): Event representing directory deletion.
        """
        # Recover and return error
        try:
            # Recover deleted file from vc so it can be deleted properly
            self._devices_manager.recover_from_version_control()
        except Exception as err:
            print_and_log("File Watcher: " + repr(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Repository reverted after %s deleted manually. Please delete files via client" % event.src_path, "MAJOR", "FILEWTCHR")

    def _check_devices_valid(self, path):
        extension = path[-4:]
        if extension != ".xml":
            raise NotConfigFileException("File not xml")

        with open(path, 'r') as synfile:
            xml_data = synfile.read()

        with self._schema_lock:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(self._schema_filepath, xml_data)

        return xml_data