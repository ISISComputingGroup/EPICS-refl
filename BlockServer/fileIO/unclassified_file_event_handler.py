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


from watchdog.events import FileSystemEventHandler

from BlockServer.core.constants import *
from reverting_file_event_handler import RevertingFileEventHandler


class UnclassifiedFileEventHandler(RevertingFileEventHandler):
    """ The DevicesFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available device screens as necessary.
    """
    def __init__(self, file_manager):
        """ Constructor.

        Args:
            file_manager (UnclassifiedFileManager): Manages IO with the VC repo
        """
        super(UnclassifiedFileEventHandler, self).__init__(file_manager)

    def _update(self, data):
        """
        Updates the files with new data.

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
        return True

    def _get_name(self, path):
        """ Not needed for devices. Stub for superclass call """
        return

    def _get_modified_message(self, name):
        """
        Returns the log message for a file event.

        Args:
            name (string): Not used for device screens, from superclass call.

        Returns (string): The message

        """
        message = "The device screens file has been modified in the filesystem, ensure it is added to version control"
        return message

    def file_modified(self, event):
        """
        Catch-all event handler.

        Args:
            event (FileSystemEvent): The event object representing the file system event
        """
        pass

    def on_deleted(self, event):
        """"
        Called when a file or directory is deleted.

        Args:
            event (DirDeletedEvent): Event representing directory deletion.
        """
        pass
