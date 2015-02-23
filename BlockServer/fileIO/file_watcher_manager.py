from threading import RLock

from watchdog.observers import Observer

from file_event_handler import ConfigFileEventHandler
from BlockServer.core.constants import CONFIG_DIRECTORY, COMPONENT_DIRECTORY


class ConfigFileWatcherManager(object):
    def __init__(self, root_path, schema_folder, config_list_manager, test_mode=False):

        schema_lock = RLock()
        self._config_dir = root_path + CONFIG_DIRECTORY
        self._comp_dir = root_path + COMPONENT_DIRECTORY

        # Create config watcher
        self._config_event_handler = ConfigFileEventHandler(root_path, schema_folder, schema_lock,
                                                            config_list_manager, test_mode=test_mode)
        self._config_observer = Observer()
        self._config_observer.schedule(self._config_event_handler, self._config_dir, recursive=True)
        self._config_observer.start()

        # Create component watcher
        self._component_event_handler = ConfigFileEventHandler(root_path, schema_folder, schema_lock,
                                                               config_list_manager, True, test_mode)
        self._component_observer = Observer()
        self._component_observer.schedule(self._component_event_handler, self._comp_dir, recursive=True)
        self._component_observer.start()

        self._error = ""
        self._warning = []

        # Used for testing
        self.has_config_event = False
        self.has_subconfig_event = False

    def pause(self):
        """ Stop the filewatcher, useful when known changes are being made through the rest of the BlockServer """
        self._component_observer.unschedule_all()
        self._config_observer.unschedule_all()

    def resume(self):
        """ Restart the filewatcher after a pause """
        # Start filewatcher threads
        self._config_observer.schedule(self._config_event_handler, self._config_dir, recursive=True)
        self._component_observer.schedule(self._component_event_handler, self._comp_dir, recursive=True)

        # Update version control

        # Update PVs