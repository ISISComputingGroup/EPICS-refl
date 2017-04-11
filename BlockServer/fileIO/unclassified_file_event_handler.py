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

from base_file_event_handler import BaseFileEventHandler
from server_common.utilities import print_and_log


class UnclassifiedFileEventHandler(BaseFileEventHandler):
    """ The UnclassifiedFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available device screens as necessary.
    """
    def __init__(self, file_manager, ignore_directories):
        """ Constructor.

        Args:
            file_manager (UnclassifiedFileManager): Manages IO with the VC repo
        """
        super(UnclassifiedFileEventHandler, self).__init__(file_manager)
        self._ignore_directories = ignore_directories

    def on_created(self, event):
        if not event.is_directory and not any(s in event.src_path for s in self._ignore_directories):
            message = "Created a new file at {0}".format(event.src_path)
            print_and_log(message)
            self._manager.add_and_commit(message, event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and not any(s in event.src_path for s in self._ignore_directories):
            message = "Deleted a file at {0}".format(event.src_path)
            print_and_log(message)
            self._manager.add_and_commit(message)

    def on_modified(self, event):
        if not event.is_directory and not any(s in event.src_path for s in self._ignore_directories):
            message = "Modified the file at {0}".format(event.src_path)
            print_and_log(message)
            self._manager.add_and_commit(message, event.src_path)

    def on_moved(self, event):
        if not event.is_directory and not any(s in event.src_path for s in self._ignore_directories):
            message = "Moved a file from {0} to {1}".format(event.src_path, event.dest_path)
            print_and_log(message)
            self._manager.add_and_commit(message)
            self._manager.add_and_commit(message, event.dest_path)

