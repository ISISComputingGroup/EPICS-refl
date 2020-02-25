from collections import namedtuple

from enum import Enum
from pcaspy import Severity

from server_common.observable import observable

StatusDescription = namedtuple("StatusDescription", [
    'display_string',   # A string representation of the server state
    'alarm_severity'])  # The alarm severity associated to this state, represented as an int (see Channel Access doc)

StatusUpdate = namedtuple("StatusUpdate", [
    'server_status',    # The server status
    'server_message'])  # The server status display message

ActiveProblemsUpdate = namedtuple("ActiveProblemsUpdate", [
    'problems_dict'])  # The dictionary of problems by source

ErrorLogUpdate = namedtuple("ErrorLogUpdate", [
    'errors'])  # The list of current error log messages


class PROBLEM(Enum):
    PLACEHOLDER = 0
    PLACEHOLDER2 = 1

    @staticmethod
    def description(problem_type):
        if problem_type is PROBLEM.PLACEHOLDER:
            return "Some placeholder description."
        if problem_type is PROBLEM.PLACEHOLDER2:
            return "Some other description."


class STATUS(Enum):
    """
    Beamline States.
    """
    INITIALISING = StatusDescription("INITIALISING", Severity.MINOR_ALARM)
    OKAY = StatusDescription("OKAY", Severity.NO_ALARM)
    CONFIG_WARNING = StatusDescription("CONFIG_WARNING", Severity.MINOR_ALARM)
    CONFIG_ERROR = StatusDescription("CONFIG_ERROR", Severity.MAJOR_ALARM)
    GENERAL_ERROR = StatusDescription("ERROR", Severity.MAJOR_ALARM)

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


@observable(StatusUpdate, ActiveProblemsUpdate, ErrorLogUpdate)
class _ServerStatusManager(object):
    """
    Handler for setting the status of the reflectometry server.
    """
    def __init__(self):
        self.status = None
        self.message = None

        self.active_problems = {}

        self.error_log = []

        self.update_status(STATUS.INITIALISING, "Reflectometry Server is initialising. Check all motor IOCs are "
                                                "running if this is taking longer than expected.")

    def clear_all(self):
        self.set_status_okay()
        self._clear_problems()
        self._clear_log()

    def _clear_problems(self):
        self.active_problems = {}
        self.trigger_listeners(ActiveProblemsUpdate(self.active_problems))

    def _clear_log(self):
        self.error_log = []
        self.trigger_listeners(ErrorLogUpdate(self.error_log))

    def update_status(self, status, message):
        """
        Update the server status and display message and notifies listeners.

        Params:
            status (StatusDescription): The updated beamline status
            message (String): The updated beamline status display message
        """
        self.status = status
        self.message = message
        self.trigger_listeners(StatusUpdate(self.status, self.message))

    def update_active_problems(self, problem_type, source):
        if problem_type in self.active_problems.keys():
            self.active_problems[problem_type].add(source)
        else:
            self.active_problems[problem_type] = {source}

        self.trigger_listeners(ActiveProblemsUpdate(self.active_problems))

    def update_log(self, message):
        self.error_log.append(message)

    def set_status_okay(self):
        """
        Convenience method to clear the server status.
        """
        self.update_status(STATUS.OKAY, "")


STATUS_MANAGER = _ServerStatusManager()
