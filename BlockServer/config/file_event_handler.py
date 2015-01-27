from watchdog.events import FileSystemEventHandler, FileDeletedEvent, FileModifiedEvent
from config_server import ConfigServerManager
from lxml import etree
from constants import *
from macros import MACROS
from server_common.utilities import print_and_log
import string
import os
from threading import RLock


class NotConfigFileException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ConfigurationIncompleteException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ConfigFileEventHandler(FileSystemEventHandler):
    def __init__(self, root_path, schema_folder, schema_lock, config_list_manager, is_subconfig=False, test_mode=False):
        self._schema_folder = schema_folder
        self._is_subconfig = is_subconfig
        self._schema_lock = schema_lock
        self._root_path = root_path
        self._config_list = config_list_manager

        # For testing
        self._event_fired = False

    def on_any_event(self, event):
        if not event.is_directory:
            if type(event) is not FileDeletedEvent:
                try:
                    self._event_fired = True

                    conf = self._check_config_valid(event.src_path)

                    # Update PVs
                    self._config_list.update_a_config_in_list_filewatcher(conf, self._is_subconfig)

                    # Update version control (add where appropriate)
                except NotConfigFileException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except ConfigurationIncompleteException as err:
                    print_and_log("File Watcher: " + str(err), "INFO")
                except etree.XMLSyntaxError as err:
                    print_and_log("File Watcher: XMLSyntax incorrect (%s)" % event.src_path, "ERROR")
                    print_and_log(str(err), "ERROR")
                except Exception as err:
                    print_and_log("File Watcher: " + str(err), "ERROR")

            else:
                pass
                # If component check dependencies and recover if required (through svn)

                # Update PVs

                # Update version control (remove)

    def _check_config_valid(self, path):
        self._check_files_correct(path)

        # Check can load into config
        config_name = self._get_config_name(path)
        ic = ConfigServerManager(self._root_path, MACROS)
        try:
            ic._load_config(config_name, self._is_subconfig)
        except Exception as err:
            print_and_log("File Watcher, loading config: " + str(err), "ERROR")

        # Return loaded config
        return ic

    def get_event_fired(self):
        # For testing purposes
        fired = self._event_fired
        self._event_fired = False
        return fired

    def _check_files_correct(self, config_xml_path):
        folder, file_name = string.rsplit(config_xml_path, '\\', 1)
        if file_name in SCHEMA_FOR:
            schema_name = string.split(file_name, '.')[0] + '.xsd'
            self._check_against_schema(config_xml_path, schema_name)# Raises Exception if bad
        else:
            raise NotConfigFileException("File not known config xml (%s)" % file_name)

        missing_files = set(SCHEMA_FOR).difference(set(os.listdir(folder)))
        if len(missing_files) != 0:
            if not (self._is_subconfig and missing_files == [FILENAME_SUBCONFIGS]):
                raise ConfigurationIncompleteException("Files missing (%s)" % ','.join(list(missing_files)))

        return True

    def _check_against_schema(self, xml_file, schema_file):
        # Import the schema file (must move to path for includes)
        with self._schema_lock:
            cur = os.getcwd()
            os.chdir(self._schema_folder)
            with open(schema_file, 'r') as f:
                schema_raw = etree.XML(f.read())

            schema = etree.XMLSchema(schema_raw)
            xmlparser = etree.XMLParser(schema=schema)
            os.chdir(cur)

        # Import the xml file
        with open(xml_file, 'r') as f:
            str = f.read()
        etree.fromstring(str, xmlparser)

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