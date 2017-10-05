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

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from server_common.utilities import print_and_log


class FileEventHandler(FileSystemEventHandler):
    """ The FileEventHandler class. Provides event handling for events on the file system.
    """

    def __init__(self, vc):
        """ Constructor.

        Args:
        manager : The File Manager.
        """

        self._vc = vc
        self._config_observer = self.create_observer(self, FILEPATH_MANAGER.config_root_dir)

    @staticmethod
    def create_observer(event_handler, directory):
        obs = Observer()
        obs.schedule(event_handler, directory, True)
        obs.start()
        return obs

    def on_created(self, event):
        pass

    def on_moved(self, event):
        pass

    def on_deleted(self, event):
        if not event.is_directory:
            path = os.path.normpath(event.src_path)
            message = "Deleted a file at {0}".format(path)
            print_and_log(message)
            self._vc.remove(path)

    def on_modified(self, event):
        if not event.is_directory:
            path = os.path.normpath(event.src_path)
            message = "Changed a file at {0}".format(path)
            print_and_log(message)
            self._vc.add(path)

    def add_and_commit(self, message, path=None):
        self._vc.add(path)
        self._vc.commit(message)
