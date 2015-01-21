from watchdog.observers import Observer
from file_event_handler import ConfigFileEventHandler
from threading import RLock

class ConfigFileWatcherManager(object):
    def __init__(self, config_folder, component_folder, schema_folder, test_mode=False):

        self._schema_lock = RLock()

        # Create config watcher
        event_handler = ConfigFileEventHandler(self, schema_folder, self._schema_lock, test_mode=test_mode)
        self._config_observer = Observer()
        self._config_observer.schedule(event_handler, config_folder, recursive=True)
        self._config_observer.start()

        # Create component watcher
        event_handler = ConfigFileEventHandler(self, schema_folder, self._schema_lock, True, test_mode)
        self._component_observer = Observer()
        self._component_observer.schedule(event_handler, component_folder, recursive=True)
        self._component_observer.start()

        self._error = ""
        self._warning = []

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

    def set_error_message(self, message):
        self.pause()
        self.pause(True)
        self._error = message

    def get_error_message(self):
        return self._error

    def set_warning_message(self, message):
        self._warning.append(message)

    def get_warning_messages(self):
        return self._warning