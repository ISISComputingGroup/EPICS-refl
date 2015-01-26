from watchdog.observers import Observer
from file_event_handler import ConfigFileEventHandler
from threading import RLock
from constants import CONFIG_DIRECTORY, COMPONENT_DIRECTORY


class ConfigFileWatcherManager(object):
    def __init__(self, root_path, schema_folder, test_mode=False):

        schema_lock = RLock()

        # Create config watcher
        self._config_event_handler = ConfigFileEventHandler(root_path, schema_folder, schema_lock, test_mode=test_mode)
        self._config_observer = Observer()
        self._config_observer.schedule(self._config_event_handler, root_path + CONFIG_DIRECTORY, recursive=True)
        self._config_observer.start()

        # Create component watcher
        self._component_event_handler = ConfigFileEventHandler(schema_folder, root_path, schema_lock, True, test_mode)
        self._component_observer = Observer()
        self._component_observer.schedule(self._component_event_handler, root_path + COMPONENT_DIRECTORY, recursive=True)
        self._component_observer.start()

        self._error = ""
        self._warning = []

        # Used for testing
        self.has_config_event = False
        self.has_subconfig_event = False

    def pause(self, is_subconfig=False):
        ''' Stop the filewatcher, useful when known changes are being made through the rest of the BlockServer '''
        if is_subconfig:
            self._component_observer.stop()
        else:
            self._config_observer.stop()

    def resume(self):
        ''' Restart the filewatcher after a pause '''
        # Start filewatcher threads
        self._config_observer.start()
        self._component_observer.start()

        # Update version control

        # Update PVs

    # Used for testing
    def config_fired(self):
        return self._config_event_handler.get_event_fired()

    def subconfig_fired(self):
        return self._component_event_handler.get_event_fired()