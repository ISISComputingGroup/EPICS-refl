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
from abc import abstractmethod

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent

from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import *
from BlockServer.core.macros import MACROS
from server_common.utilities import print_and_log
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.fileIO.schema_checker import ConfigurationIncompleteException, NotConfigFileException
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from BlockServer.synoptic.synoptic_manager import SYNOPTIC_SCHEMA_FILE


class BaseFileEventHandler(FileSystemEventHandler):
    """ The SomeFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module.
    Superclass for individual file event handler classes for different kinds of configuration files.
    """

    def __init__(self, schema_folder, schema_lock, manager):
        """Constructor.

        Args:
            schema_folder (string): The location of the schemas
            schema_lock (string): The reentrant lock for the schema
            manager : The File Manager # TODO needed methods
        """
        self._schema_filepath = os.path.join(schema_folder, SYNOPTIC_SCHEMA_FILE)
        self._schema_lock = schema_lock
        self._manager = manager

    def on_any_event(self, event):
        """Catch-all event handler.

        Args:
            event (FileSystemEvent): The event object representing the file system event
        """
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    name = self._get_name(event.src_path)
                    if type(event) is FileMovedEvent:
                        modified_path = event.dest_path
                        self._manager.delete(name)
                    else:
                        modified_path = event.src_path

                    data = self._check_valid(modified_path)

                    # Update PVs
                    self._update(name, data)

                    # Inform user
                    print_and_log("The synoptic, %s, has been modified in the filesystem, ensure it is added to "
                                  "version control" % name, "INFO", "FILEWTCHR")

                except NotConfigFileException as err:
                    print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
                except Exception as err:
                    print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

    def on_deleted(self, event):
        """"Called when a file or directory is deleted.

        Args:
            event (DirDeletedEvent): Event representing directory deletion.
        """
        # Recover and return error
        try:
            # Recover deleted file from vc so it can be deleted properly
            self._manager.recover()
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Repository reverted after %s deleted manually. Please delete files via client" % event.src_path, "MAJOR", "FILEWTCHR")


