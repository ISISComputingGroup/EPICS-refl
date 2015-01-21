class MockWatcherManager(object):
    def __init__(self):
        self._error = ""
        self._warning = []

    def set_error_message(self, message):
        self._error = message

    def get_error_message(self):
        return self._error

    def set_warning_message(self, message):
        self._warning.append(message)

    def get_warning_messages(self):
        return self._warning