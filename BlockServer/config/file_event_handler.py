from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileModifiedEvent
from config_server import ConfigServerManager
from constants import *
from macros import MACROS
from server_common.utilities import print_and_log
import string
from schema_checker import ConfigurationSchemaChecker
from schema_checker import ConfigurationIncompleteException, NotConfigFileException


class ConfigFileEventHandler(FileSystemEventHandler):
    def __init__(self, root_path, schema_folder, schema_lock, config_list_manager, is_subconfig=False, test_mode=False):
        self._schema_folder = schema_folder
        self._is_subconfig = is_subconfig
        self._schema_lock = schema_lock
        self._root_path = root_path
        self._config_list = config_list_manager

    def on_any_event(self, event):
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    conf = self._check_config_valid(event.src_path)

                    # Update PVs
                    self._config_list.update_a_config_in_list_filewatcher(conf, self._is_subconfig)

                    # Update version control (add where appropriate)
                except NotConfigFileException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except Exception as err:
                    print_and_log("File Watcher: " + str(err), "ERROR")

            else:
                pass
                # If component check dependencies and recover if required (through svn)

                # Update PVs

                # Update version control (remove)

    def _check_config_valid(self, path):
        with self._schema_lock:
            ConfigurationSchemaChecker.check_config_file_correct(self._schema_folder, path, self._is_subconfig)

        # Check can load into config
        config_name = self._get_config_name(path)
        ic = ConfigServerManager(self._root_path, MACROS)
        try:
            ic._load_config(config_name, self._is_subconfig)
        except Exception as err:
            print_and_log("File Watcher, loading config: " + str(err), "ERROR")

        # Return loaded config
        return ic

    def _get_config_name(self, path):
        if not self._is_subconfig:
            rel_path = string.replace(path, self._root_path + CONFIG_DIRECTORY, '')
        else:
            rel_path = string.replace(path, self._root_path + COMPONENT_DIRECTORY, '')
        folders = string.split(rel_path, '\\')
        if len(folders) < 2:
            raise NotConfigFileException("File in root directory")
        else:
            return folders[0]