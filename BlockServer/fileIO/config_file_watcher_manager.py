'''
This file is part of the ISIS IBEX application.
Copyright (C) 2012-2015 Science & Technology Facilities Council.
All rights reserved.

This program is distributed in the hope that it will be useful.
This program and the accompanying materials are made available under the
terms of the Eclipse Public License v1.0 which accompanies this distribution.
EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.

You should have received a copy of the Eclipse Public License v1.0
along with this program; if not, you can obtain a copy from
https://www.eclipse.org/org/documents/epl-v10.php or 
http://opensource.org/licenses/eclipse-1.0.php
'''
from threading import RLock
import os

from watchdog.observers import Observer

from BlockServer.fileIO.config_file_event_handler import ConfigFileEventHandler
from BlockServer.fileIO.synoptic_file_event_handler import SynopticFileEventHandler
from BlockServer.core.file_path_manager import FILEPATH_MANAGER

import os


class ConfigFileWatcherManager(object):
    """ The ConfigFileWatcherManager class.

    Registers and communicates with the event handlers for configuration and synoptic filewatchers.
    """
    def __init__(self, schema_folder, config_list_manager, synoptic_manager):
        """Constructor.

        Args:
            schema_folder (string): The folder where the schemas are kept.
            config_list_manager (ConfigListManager): The ConfigListManager instance.
            synoptic_manager (SynopticManager): The SynopticManager instance.
        """
        schema_lock = RLock()
        self._config_dir = FILEPATH_MANAGER.config_dir
        self._comp_dir = FILEPATH_MANAGER.component_dir
        self._syn_dir = FILEPATH_MANAGER.synoptic_dir
        self._observers = []

        # Create config watcher
        self._config_event_handler = ConfigFileEventHandler(schema_folder, schema_lock,
                                                            config_list_manager)

        self._config_observer = self._create_observer(self._config_event_handler, self._config_dir)

        # Create component watcher
        self._component_event_handler = ConfigFileEventHandler(schema_folder, schema_lock,
                                                               config_list_manager, True)

        self._component_observer = self._create_observer(self._component_event_handler, self._comp_dir)

        # Create synoptic watcher
        self._synoptic_event_handler = SynopticFileEventHandler(schema_folder, schema_lock,
                                                                synoptic_manager)

        self._syn_observer = self._create_observer(self._synoptic_event_handler, self._syn_dir)

    def _create_observer(self, event_handler, directory):
        obs = Observer()
        obs.schedule(event_handler, directory, True)
        obs.start()
        return obs

    def pause(self):
        """Stop the filewatcher, useful when known changes are being made through the rest of the BlockServer."""
        self._component_observer.unschedule_all()
        self._config_observer.unschedule_all()
        self._syn_observer.unschedule_all()

    def resume(self):
        """Restart the filewatcher after a pause."""
        # Start filewatcher threads
        self._config_observer.schedule(self._config_event_handler, self._config_dir, recursive=True)
        self._component_observer.schedule(self._component_event_handler, self._comp_dir, recursive=True)
        self._syn_observer.schedule(self._synoptic_event_handler, self._syn_dir, recursive=True)
