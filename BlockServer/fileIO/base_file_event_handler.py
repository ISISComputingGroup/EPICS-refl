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

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent


class BaseFileEventHandler(FileSystemEventHandler):
    """ The BaseFileEventHandler class
        Inherit from this class to provide event handling for configuration files which should be reverted on change.
        Subclass must implement :
            _get_name: returns the name of the configuration, extracted from the event source path.
            _check_valid: checks whether the configuration file is valid and returns the content if so.
            _update: updates the configuration with new data read from the modified file.
            _get_modified_message: Returns the string message to be logged when file is modified.

    """

    def __init__(self, manager):
        """ Constructor.

        Args:
        manager : The File Manager. Must implement the following methods:
        delete: Deletes a specific configuration from the internal list of available ones.
        recover_from_version_control: Reverts the config directory back to the state held in version control.
        """

        self._manager = manager

    def on_created(self, event):
        raise NotImplementedError()

    def on_modified(self, event):
        raise NotImplementedError()

    def on_moved(self, event):
        raise NotImplementedError()

    def on_deleted(self, event):
        raise NotImplementedError()


