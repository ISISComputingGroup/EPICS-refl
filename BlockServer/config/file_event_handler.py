from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileMovedEvent
from config_server import ConfigServerManager
from constants import *
from macros import MACROS
from server_common.utilities import print_and_log
import string
import os
from schema_checker import ConfigurationSchemaChecker
from schema_checker import ConfigurationIncompleteException, NotConfigFileException
from config.file_manager import ConfigurationFileManager


class ConfigFileEventHandler(FileSystemEventHandler):
    def __init__(self, root_path, schema_folder, schema_lock, config_list_manager, is_subconfig=False, test_mode=False):
        self._schema_folder = schema_folder
        self._is_subconfig = is_subconfig
        self._schema_lock = schema_lock
        self._root_path = root_path
        self._config_list = config_list_manager
        self._test_mode = test_mode

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

                    # Update version control (add where appropriate)
                    if not self._test_mode:
                        ConfigurationFileManager.add_configs_to_version_control(self._watching_path,
                                                                                [conf.get_config_name()],
                                                                                "Files modified by hand")
                except NotConfigFileException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except Exception as err:
                    print_and_log("File Watcher: " + str(err), "ERROR")

    def on_deleted(self, event):
        try:
            # Recover deleted file from vc so it can be deleted properly
            # TODO: Ignore the new files in modified
            ConfigurationFileManager.recover_from_version_control(self._root_path)
        except Exception as err:
            print_and_log("File Watcher: " + str(err), "ERROR")

        try:
            if self._check_file_at_root(event.src_path):
                if os.path.isdir(event.src_path):
                    # Deleting a whole config
                    self._config_list.delete_configs([self._get_config_name(event.src_path)], self._is_subconfig)
                else:
                    raise NotConfigFileException("")
            else:
                # Check if we're deleting a file required for a config
                self._check_config_valid(event.src_path)

                print_and_log("File Watcher: File part of config (%s), restored from version control" % event.src_path)

        except NotConfigFileException:
            ConfigurationFileManager.delete_file_from_version_control(self._watching_path, event.src_path,
                                                                      "Deleted by hand")
        except Exception as err:
            print_and_log("File Watcher: " + str(err))

    def _check_config_valid(self, path):
        if self._check_file_at_root(path):
            raise NotConfigFileException("File in root directory")

        with self._schema_lock:
            ConfigurationSchemaChecker.check_matches_schema(self._schema_folder, path, self._is_subconfig)

        # Check can load into config
        ic = ConfigServerManager(self._root_path, MACROS)
        try:
            ic._load_config(self._get_config_name(path), self._is_subconfig)
        except Exception as err:
            print_and_log("File Watcher, loading config: " + str(err), "ERROR")

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