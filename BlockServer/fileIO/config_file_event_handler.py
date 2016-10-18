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
import string

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent

from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from server_common.utilities import print_and_log
from schema_checker import ConfigurationSchemaChecker
from schema_checker import ConfigurationIncompleteException, NotConfigFileException


class ConfigFileEventHandler(FileSystemEventHandler):
    """ The ConfigFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available configurations as necessary.
    """

    def __init__(self, schema_folder, schema_lock, config_list_manager, is_component=False):
        """Constructor.

        Args:
            schema_folder (string): The location of the schemas
            config_list_manager (ConfigListManager): The ConfigListManager
            is_component (bool): Whether it is a component or not
        """
        self._schema_folder = schema_folder
        self._is_comp = is_component
        self._schema_lock = schema_lock
        self._config_list = config_list_manager

        if self._is_comp:
            self._watching_path = FILEPATH_MANAGER.component_dir
        else:
            self._watching_path = FILEPATH_MANAGER.config_dir

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
                        self._config_list.delete_configs([self._get_config_name(event.src_path)], self._is_comp)
                    else:
                        modified_path = event.src_path

                    conf = self._check_config_valid(modified_path)

                    # Update PVs
                    self._config_list.update_a_config_in_list_filewatcher(conf, self._is_comp)

                    # Inform user
                    print_and_log("The configuration, %s, has been modified in the filesystem, ensure it is added to "
                                  "version control" % conf.get_config_name(), "INFO", "FILEWTCHER")

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
            self._config_list.recover_from_version_control()
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Repository reverted after %s deleted manually. Please delete files via client" % event.src_path, "MAJOR", "FILEWTCHR")

    def _check_config_valid(self, path):
        if self._check_file_at_root(path):
            raise NotConfigFileException("File in root directory")

        with self._schema_lock:
            # Check can load into config - schema is checked on load
            try:
                ic = self._config_list.load_config(self._get_config_name(path), self._is_comp)
            except Exception as err:
                print_and_log("File Watcher, loading config: " + str(err), "INFO", "FILEWTCHR")

        return ic

    def _split_config_path(self, path):
        """Splits the given path into its components after removing the root path.

        Args:
            path (string): The path to be split

        Returns:
            list : The parts of the file path in order
        """
        if not self._is_comp:
            rel_path = string.replace(path, FILEPATH_MANAGER.config_dir, '')
        else:
            rel_path = string.replace(path, FILEPATH_MANAGER.component_dir, '')

        if rel_path.startswith(os.sep):
            # Remove stray separator
            rel_path = rel_path[1:]

        folders = string.split(rel_path, os.sep)
        return folders

    def _check_file_at_root(self, path):
        folders = self._split_config_path(path)
        if len(folders) < 2:
            return True
        else:
            return False

    def _get_config_name(self, path):
        return self._split_config_path(path)[0]

