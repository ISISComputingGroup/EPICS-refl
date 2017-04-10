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
from base_file_event_handler import BaseFileEventHandler


class UnclassifiedFileEventHandler(BaseFileEventHandler):
    """ The UnclassifiedFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available device screens as necessary.
    """
    def __init__(self, file_manager):
        """ Constructor.

        Args:
            file_manager (UnclassifiedFileManager): Manages IO with the VC repo
        """
        super(UnclassifiedFileEventHandler, self).__init__(file_manager)

    def on_created(self, event):
        self._manager.commit("Created a new file.")

    def on_deleted(self, event):
        self._manager.commit("Deleted a file.")

    def on_modified(self, event):
        self._manager.commit("Modified a file.")

    def on_moved(self, event):
        self._manager.commit("Moved a file.")

