from threading import RLock

from watchdog.observers import Observer

from config_file_event_handler import ConfigFileEventHandler
from synoptic_file_event_handler import SynopticFileEventHandler
from BlockServer.core.constants import CONFIG_DIRECTORY, COMPONENT_DIRECTORY, SYNOPTIC_DIRECTORY


class ConfigFileWatcherManager(object):
    """ The ConfigFileWatcherManager class.

    Registers and communicates with the event handlers for configuration and synoptic filewatchers.
    """
    def __init__(self, root_path, schema_folder, config_list_manager, synoptic_list_manager, test_mode=False):
        """Constructor.

        Args:
            root_path (string) : The root folder where configurations are stored
            schema_folder (string) : The folder where the schemas are kept
            config_list_manager (ConfigListManager) : The ConfigListManager
            test_mode (bool) : Whether to start in test mode
        """
        schema_lock = RLock()
        self._config_dir = root_path + CONFIG_DIRECTORY
        self._comp_dir = root_path + COMPONENT_DIRECTORY
        self._syn_dir = root_path + SYNOPTIC_DIRECTORY
        self._observers = []

        # Create config watcher
        self._config_event_handler = ConfigFileEventHandler(root_path, schema_folder, schema_lock,
                                                            config_list_manager, test_mode=test_mode)

        self._config_observer = self._create_observer(self._config_event_handler, self._config_dir)

        # Create component watcher
        self._component_event_handler = ConfigFileEventHandler(root_path, schema_folder, schema_lock,
                                                               config_list_manager, True, test_mode)

        self._component_observer = self._create_observer(self._component_event_handler, self._comp_dir)

        # Create synoptic watcher
        self._synoptic_event_handler = SynopticFileEventHandler(root_path, schema_folder, schema_lock,
                                                                synoptic_list_manager, test_mode)

        self._syn_observer = self._create_observer(self._synoptic_event_handler, self._syn_dir)

    def _create_observer(self, event_handler, directory):
        obs = Observer()
        obs.schedule(event_handler, directory, True)
        obs.start()
        return obs

    def pause(self):
        """Stop the filewatcher, useful when known changes are being made through the rest of the BlockServer."""
        self._component_observer.unschedule_all()
        self._config_observer.unschedule_all()
        self._syn_observer.unschedule_all()

    def resume(self):
        """Restart the filewatcher after a pause."""
        # Start filewatcher threads
        self._config_observer.schedule(self._config_event_handler, self._config_dir, recursive=True)
        self._component_observer.schedule(self._component_event_handler, self._comp_dir, recursive=True)
        self._syn_observer.schedule(self._synoptic_event_handler, self._syn_dir, recursive=True)