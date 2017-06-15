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

from watchdog.events import FileDeletedEvent, FileMovedEvent

from server_common.utilities import print_and_log
from BlockServer.fileIO.schema_checker import ConfigurationIncompleteException, NotConfigFileException
from base_file_event_handler import BaseFileEventHandler


class RevertingFileEventHandler(BaseFileEventHandler):
    """ The RevertingFileEventHandler class
        Inherit from this class to provide event handling for configuration files which should be reverted on change.
        Subclass must implement :
            _get_name: returns the name of the configuration, extracted from the event source path.
            _check_valid: checks whether the configuration file is valid and returns the content if so.
            _update: updates the configuration with new data read from the modified file.
            _get_modified_message: Returns the string message to be logged when file is modified.

    """

    def _file_modified(self, event):
        """ Called when a file was modified.

        Args:
            event (FileSystemEvent): The event object representing the file system event
        """
        if event.is_directory:
            return

        try:
            name = self._get_name(event.src_path)
            modified_path = event.src_path

            data = self._check_valid(modified_path)

            self._update_pvs(data)
            self._inform_user(name)

        except NotConfigFileException as err:
            print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
        except ConfigurationIncompleteException as err:
            print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

    def _directory_modified(self, event):
        """ Called when a directory was modified.

            Args:
                event (FileSystemEvent): The event object representing the file system event
        """

        # No default behaviour.
        pass

    def _filesystem_modified(self, event):
        """ Called when a file or directory was modified.

            Args:
                event (FileSystemEvent): The event object representing the file system event
        """
        if event.is_directory:
            self._directory_modified(event)
        else:
            self._file_modified(event)

    def on_created(self, event):
        """ Called when a file was created. Overrides method from BaseFileEventHandler

            Args:
                event (FileSystemEvent): The event object representing the file system event
        """
        self._filesystem_modified(event)

    def on_modified(self, event):
        """ Called when a file was modified. Overrides method from BaseFileEventHandler

            Args:
                event (FileSystemEvent): The event object representing the file system event
        """
        self._filesystem_modified(event)

    def on_moved(self, event):
        """ Called when a file was moved. Overrides method from BaseFileEventHandler

        Args:
            event (FileSystemEvent): The event object representing the file system event
        """
        if event.is_directory:
            return

        try:
            name = self._get_name(event.src_path)
            # Renaming a file triggers this
            modified_path = event.dest_path
            self._manager.delete(name)

            data = self._check_valid(modified_path)

            self._update_pvs(data)
            self._inform_user(name)

        except NotConfigFileException as err:
            print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
        except ConfigurationIncompleteException as err:
            print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

    def on_deleted(self, event):
        """ Called when a file was deleted. Overrides method from BaseFileEventHandler

            Args:
                event (FileSystemEvent): The event object representing the file system event
        """
        # Recover and return error
        try:
            # Recover deleted file from vc so it can be deleted properly
            self._manager.recover_from_version_control()
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Repository reverted after %s deleted manually. "
                      "Please delete files via client" % event.src_path, "MAJOR", "FILEWTCHR")

    def _update_pvs(self, data):
        self._update(data)

    def _inform_user(self, name):
        print_and_log(self._get_modified_message(name), "INFO", "FILEWTCHR")


