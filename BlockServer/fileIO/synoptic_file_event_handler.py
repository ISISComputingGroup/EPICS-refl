import string
import os

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent

from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import *
from BlockServer.core.macros import MACROS
from server_common.utilities import print_and_log
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker
from BlockServer.fileIO.schema_checker import ConfigurationIncompleteException, NotConfigFileException
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from BlockServer.core.synoptic_manager import SYNOPTIC_SCHEMA


class SynopticFileEventHandler(FileSystemEventHandler):
    """ The SynopticFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available synoptics as necessary.
    """
    def __init__(self, root_path, schema_folder, schema_lock, synoptic_list_manager):
        """Constructor.

        Args:
            root_path (string) : The location of the configurations and components
            schema_folder (string) : The location of the schema
            synoptic_list_manager (SynopticListManager) : The SynopticListManager
        """
        self._schema_filepath = schema_folder + "\\" + SYNOPTIC_SCHEMA
        self._schema_lock = schema_lock
        self._root_path = root_path
        self._synoptic_list = synoptic_list_manager

    def on_any_event(self, event):
        """Catch-all event handler.

        Args:
            event (FileSystemEvent) : The event object representing the file system event
        """
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    name = self._get_synoptic_name(event.src_path)
                    if type(event) is FileMovedEvent:
                        modified_path = event.dest_path
                        self._synoptic_list.delete_synoptics([name])
                    else:
                        modified_path = event.src_path

                    syn = self._check_synoptic_valid(modified_path)

                    # Update PVs
                    self._synoptic_list.update_from_filewatcher(name, syn)

                    # Inform user
                    print_and_log("The synoptic, %s, has been modified in the filesystem, ensure it is added to "
                                  "version control" % name, "INFO", "FILEWTCHER")

                except NotConfigFileException as err:
                    print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher: " + str(err), src="FILEWTCHR")
                except Exception as err:
                    print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

    def on_deleted(self, event):
        """"Called when a file or directory is deleted.

        Args:
            event (DirDeletedEvent) : Event representing directory deletion.
        """
        # Recover and return error
        try:
            # Recover deleted file from vc so it can be deleted properly
            self._synoptic_list.recover_from_version_control()
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Recovered %s, please delete via client" % event.src_path, "MAJOR", "FILEWTCHR")

    def _check_synoptic_valid(self, path):
        extension = path[-4:]
        if extension != ".xml":
            raise NotConfigFileException("File not xml")

        with open(path, 'r') as synfile:
            xml_data = synfile.read()

        with self._schema_lock:
            ConfigurationSchemaChecker.check_synoptic_matches_schema(self._schema_filepath, xml_data)

        return xml_data

    def _get_synoptic_name(self, path):
        return os.path.basename(path)[:-4]