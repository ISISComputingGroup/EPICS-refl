from watchdog.events import FileSystemEventHandler
from lxml import etree
from constants import VALID_FILENAMES
import string
import os
class ConfigFileEventHandler(FileSystemEventHandler):
    def __init__(self, parent, schema_folder, schema_lock, is_subconfig=False, test_mode=False):
        self._schema_folder = schema_folder
        self._is_subconfig = is_subconfig
        self._schema_lock = schema_lock
        self._parent = parent

    def on_created(self, event):
        if not event.is_directory:
            self._check_config_valid(event.src_path)

            # Update PVs

            # Add to version control

    def on_modified(self, event):
        if not event.is_directory:
            self._check_config_valid(event.src_path)

            # Update PVs

            # Update version control

    def on_moved(self, event):
        self._check_config_valid(event.dest_path)

        # Update PVs

        # Update version control

    def on_deleted(self, event):
        pass
        # If component check dependencies and recover if required (through svn)

        # Update PVs

        # Update version control

    def _check_config_valid(self, path):
        self._check_files_correct(path)

        # Check can load into config

        # Check not active or component of active

        # Return loaded config

    def _check_files_correct(self, config_xml_path):
        file_name = string.rsplit(config_xml_path, '\\', 1)[1]
        print "File is " + file_name
        if file_name in VALID_FILENAMES:
            schema_name = string.split(file_name, '.')[0] + '.xsd'
            try:
                self._check_against_schema(config_xml_path, schema_name)
            except Exception as err:
                self._parent.set_error_message(err.message)
        else:
            self._parent.set_warning_message("Non-Config file found")

    def _check_against_schema(self, xml_file, schema_file):
        # Import the schema file (must move to path for includes)
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