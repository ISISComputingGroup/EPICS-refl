from collections import namedtuple

from enum import Enum
from pcaspy import Severity

from server_common.observable import observable

ServerStatus = namedtuple("ServerStatus", [
    'display_string',   # A string representation of the server state
    'alarm_severity'])  # The alarm severity associated to this state, represented as an int (see Channel Access doc)

StatusUpdate = namedtuple("StatusUpdate", [
    'server_status',    # The server status
    'server_message'])  # The server status display message


class STATUS(Enum):
    """
    Beamline States.
    """
    INITIALISING = ServerStatus("INITIALISING", Severity.MINOR_ALARM)
    OKAY = ServerStatus("OKAY", Severity.NO_ALARM)
    CONFIG_WARNING = ServerStatus("CONFIG_WARNING", Severity.MINOR_ALARM)
    CONFIG_ERROR = ServerStatus("CONFIG_ERROR", Severity.MAJOR_ALARM)
    GENERAL_ERROR = ServerStatus("ERROR", Severity.MAJOR_ALARM)

    @staticmethod
    def status_codes():
        """
        Returns:
            (list[str]) status codes for the beamline
        """
        # noinspection PyTypeChecker
        return [status.value for status in STATUS]

    @property
    def display_string(self):
        """
        Returns: display string for the enum
        """
        return self.value.display_string

    @property
    def alarm_severity(self):
        """
        Returns: Alarm severity of beamline status
        """
        return self.value.alarm_severity


@observable(StatusUpdate)
class _ServerStatusManager(object):
    """
    Handler for setting the status of the reflectometry server.
    """
    def __init__(self):
        self.status = None
        self.message = None

    def update_status(self, status, message):
        """
        Update the server status and display message and notifies listeners.

        Params:
            status (ServerStatus): The updated beamline status
            message (String): The updated beamline status display message
        """
        self.status = status
        self.message = message
        self.trigger_listeners(StatusUpdate(self.status, self.message))

    def set_status_okay(self):
        """
        Convenience method to clear the server status.
        """
        self.update_status(STATUS.OKAY, "")


STATUS_MANAGER = _ServerStatusManager()
