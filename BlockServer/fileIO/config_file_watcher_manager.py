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

from threading import RLock

from watchdog.observers import Observer

from BlockServer.fileIO.config_file_event_handler import ConfigFileEventHandler
from BlockServer.fileIO.devices_file_event_handler import DevicesFileEventHandler
from BlockServer.fileIO.synoptic_file_event_handler import SynopticFileEventHandler
from BlockServer.fileIO.unclassified_file_event_handler import UnclassifiedFileEventHandler
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from BlockServer.fileIO.unclassified_file_manager import UnclassifiedFileManager


class ConfigFileWatcherManager(object):
    """ The ConfigFileWatcherManager class.

    Registers and communicates with the event handlers for configuration and synoptic filewatchers.
    """
    def __init__(self, schema_folder, config_list_manager, synoptic_manager, devices_manager):
        """Constructor.

        Args:
            schema_folder (string): The folder where the schemas are kept.
            config_list_manager (ConfigListManager): The ConfigListManager instance.
            synoptic_manager (SynopticManager): The SynopticManager instance.
            devices_manager (DevicesManager): The DevicesManager instance.
        """
        schema_lock = RLock()
        self._config_dir = FILEPATH_MANAGER.config_dir
        self._comp_dir = FILEPATH_MANAGER.component_dir
        self._syn_dir = FILEPATH_MANAGER.synoptic_dir
        self._dev_dir = FILEPATH_MANAGER.devices_dir
        self._config_root = FILEPATH_MANAGER.config_root_dir
        self._scripts_dir = FILEPATH_MANAGER.scripts_dir

        # Create config watcher
        self._config_event_handler = ConfigFileEventHandler(schema_lock, config_list_manager)
        self._config_observer = self._create_observer(self._config_event_handler, self._config_dir)

        # Create component watcher
        self._component_event_handler = ConfigFileEventHandler(schema_lock, config_list_manager, True)
        self._component_observer = self._create_observer(self._component_event_handler, self._comp_dir)

        # Create synoptic watcher
        self._synoptic_event_handler = SynopticFileEventHandler(schema_folder, schema_lock, synoptic_manager)
        self._syn_observer = self._create_observer(self._synoptic_event_handler, self._syn_dir)

        # Create device screens watcher
        self._devices_event_handler = DevicesFileEventHandler(schema_folder, schema_lock, devices_manager)
        self._dev_observer = self._create_observer(self._devices_event_handler, self._dev_dir)

        # Create everything else watcher
        ignore_directories = [self._config_dir, self._comp_dir, self._syn_dir, self._dev_dir]
        self._unclassified_file_event_handler = UnclassifiedFileEventHandler(UnclassifiedFileManager(config_list_manager), ignore_directories)
        self._other_observer = self._create_observer(self._unclassified_file_event_handler, self._config_root)

        # Create script watcher
        self._script_event_handler = UnclassifiedFileEventHandler(UnclassifiedFileManager(config_list_manager), [])
        self._script_observer = self._create_observer(self._script_event_handler, self._scripts_dir)

    def _create_observer(self, event_handler, directory):
        obs = Observer()
        obs.schedule(event_handler, directory, True)
        obs.start()
        return obs

    def pause(self):
        """Stop the filewatcher, useful when known changes are being made through the rest of the BlockServer."""
        for o in [self._component_observer, self._config_observer, self._syn_observer, self._dev_observer,
                     self._other_observer]:
            o.unschedule_all()

    def resume(self):
        """Restart the filewatcher after a pause."""
        # Start filewatcher threads
        self._config_observer.schedule(self._config_event_handler, self._config_dir, recursive=True)
        self._component_observer.schedule(self._component_event_handler, self._comp_dir, recursive=True)
        self._syn_observer.schedule(self._synoptic_event_handler, self._syn_dir, recursive=True)
        self._dev_observer.schedule(self._devices_event_handler, self._dev_dir, recursive=True)
        self._other_observer.schedule(self._unclassified_file_event_handler, self._config_root, recursive=True)
