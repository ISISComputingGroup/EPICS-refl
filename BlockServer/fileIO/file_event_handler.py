import string
import os

from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent

from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.constants import *
from BlockServer.core.macros import MACROS
from server_common.utilities import print_and_log
from schema_checker import ConfigurationSchemaChecker
from schema_checker import ConfigurationIncompleteException, NotConfigFileException
from BlockServer.fileIO.file_manager import ConfigurationFileManager


class ConfigFileEventHandler(FileSystemEventHandler):
    """ The ConfigFileEventHandler class

    Subclasses the FileSystemEventHandler class from the watchdog module. Handles all events on the filesystem and
    creates/removes available configurations as necessary.
    """
    def __init__(self, root_path, schema_folder, schema_lock, config_list_manager, is_subconfig=False, test_mode=False):
        self._schema_folder = schema_folder
        self._is_subconfig = is_subconfig
        self._schema_lock = schema_lock
        self._root_path = root_path
        self._config_list = config_list_manager
        self._test_mode = test_mode
        self.last_delete = ""

        if self._is_subconfig:
            self._watching_path = self._root_path + COMPONENT_DIRECTORY
        else:
            self._watching_path = self._root_path + CONFIG_DIRECTORY

    def on_any_event(self, event):
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    if type(event) is FileMovedEvent:
                        modified_path = event.dest_path
                        self._config_list.delete_configs([self._get_config_name(event.src_path)], self._is_subconfig)
                    else:
                        modified_path = event.src_path

                    conf = self._check_config_valid(modified_path)

                    # Update PVs
                    self._config_list.update_a_config_in_list_filewatcher(conf, self._is_subconfig)

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
        # Recover and return error
        try:
            # Recover deleted file from vc so it can be deleted properly
            # TODO: Ignore the new fileIO in modified
            ConfigurationFileManager.recover_from_version_control(self._root_path)
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "MAJOR", "FILEWTCHR")

        print_and_log("File Watcher: Recovered %s, please delete via client" % event.src_path, "MAJOR", "FILEWTCHR")

    def _check_config_valid(self, path):
        if self._check_file_at_root(path):
            raise NotConfigFileException("File in root directory")

        with self._schema_lock:
            ConfigurationSchemaChecker.check_config_file_matches_schema(self._schema_folder, path, self._is_subconfig)

        # Check can load into config
        try:
            ic = self._config_list.load_config(self._get_config_name(path), self._is_subconfig)
        except Exception as err:
            print_and_log("File Watcher, loading config: " + str(err), "INFO", "FILEWTCHR")

        return ic

    def _split_config_folders(self, path):
        if not self._is_subconfig:
            rel_path = string.replace(path, self._root_path + CONFIG_DIRECTORY, '')
        else:
            rel_path = string.replace(path, self._root_path + COMPONENT_DIRECTORY, '')
        folders = string.split(rel_path, '\\')
        return folders

    def _check_file_at_root(self, path):
        folders = self._split_config_folders(path)
        if len(folders) < 2:
            return True
        else:
            return False

    def _get_config_name(self, path):
        return self._split_config_folders(path)[0]