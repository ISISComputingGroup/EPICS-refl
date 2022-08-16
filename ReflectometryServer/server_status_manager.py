import logging
from collections import namedtuple

from enum import Enum
from typing import Optional

from pcaspy import Severity

from server_common.observable import observable

StatusDescription = namedtuple("StatusDescription", [
    'display_string',   # A string representation of the server state
    'alarm_severity'])  # The alarm severity associated to this state, represented as an int (see Channel Access doc)

StatusUpdate = namedtuple("StatusUpdate", [
    'server_status',    # The server status
    'server_message'])  # The server status display message

ProblemInfo = namedtuple("ProblemInfo", [
    'description',      # The problem description
    'source',           # The problem source
    'severity'])        # The severity of the problem

ActiveProblemsUpdate = namedtuple("ActiveProblemsUpdate", [
    'errors',           # Dictionary of errors (description:sources)
    'warnings',         # Dictionary of warnings (description:sources)
    'other'])           # Dictionary of other problems (description:sources)

ErrorLogUpdate = namedtuple("ErrorLogUpdate", [
    'log_as_string'])          # The current error log as a list of strings


logger = logging.getLogger(__name__)


class STATUS(Enum):
    """
    Beamline States.
    """
    INITIALISING = StatusDescription("INITIALISING", Severity.MINOR_ALARM)
    OKAY = StatusDescription("OKAY", Severity.NO_ALARM)
    WARNING = StatusDescription("WARNING", Severity.MINOR_ALARM)
    ERROR = StatusDescription("ERROR", Severity.MAJOR_ALARM)
    UNKNOWN = StatusDescription("UNKNOWN", Severity.INVALID_ALARM)

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
class _ServerStatusManager:
    """
    Handler for setting the status of the reflectometry server.
    """
    INITIALISING_MESSAGE = "Reflectometry Server is initialising. Check configurations is correct and all motor IOCs " \
                           "are running if this is taking longer than expected."

    def __init__(self):
        self._reset()

    def _reset(self):
        self._status = STATUS.OKAY
        self._message = ""
        self._error_log = []
        self._initialising = True

        self.active_errors = {}
        self.active_warnings = {}
        self.active_other_problems = {}

    def set_initialised(self):
        """
        Marks initialisation of the reflectometry server as finished.
        """
        self._initialising = False
        self._trigger_status_update()

    def clear_all(self):
        """
        Clears all current issues and log messages.
        """
        self._clear_status()
        self._clear_problems()
        self._clear_log()

    def _clear_status(self):
        self._status = STATUS.OKAY
        self._message = ""
        self._trigger_status_update()

    def _clear_problems(self):
        self.active_errors = {}
        self.active_warnings = {}
        self.active_other_problems = {}
        self._update_status()
        self._trigger_active_problems_update()

    def _clear_log(self):
        self._error_log = []
        self._trigger_error_log_update()

    def _get_problems_by_severity(self, severity):
        if severity is Severity.MAJOR_ALARM:
            return self.active_errors
        elif severity is Severity.MINOR_ALARM:
            return self.active_warnings
        else:
            return self.active_other_problems

    def _get_highest_error_level(self):
        if self.active_errors:
            return STATUS.ERROR
        elif self.active_warnings:
            return STATUS.WARNING
        elif self.active_other_problems:
            return STATUS.UNKNOWN
        else:
            return STATUS.OKAY

    def _update_status(self):
        """
        Update the server status and display message and notifies listeners.

        Params:
            status (StatusDescription): The updated beamline status
            message (String): The updated beamline status display message
        """
        self._status = self._get_highest_error_level()
        self._trigger_status_update()

    def _trigger_status_update(self):
        self.trigger_listeners(StatusUpdate(self._status, self._message))

    def _trigger_active_problems_update(self):
        self.trigger_listeners(
            ActiveProblemsUpdate(self.active_errors, self.active_warnings, self.active_other_problems))

    def _trigger_error_log_update(self):
        self.trigger_listeners(ErrorLogUpdate(self._error_log_as_string()))

    def update_active_problems(self, problem):
        """
        Updates the active problems known to the status manager. If the problem is already known, it just appends the
        new source.

        If problems are the same they should have the same description where possible but different sources
        in the front end the status box can read XXX problem (X times). Instead of listing the same problem X times and
        hiding other issues. Full error is found in the log tab.

        Params:
            problem(ProblemInfo): The problem to add
        """
        dict_to_append = self._get_problems_by_severity(problem.severity)

        if problem.description in dict_to_append.keys():
            dict_to_append[problem.description].add(problem.source)
        else:
            dict_to_append[problem.description] = {problem.source}

        self.message = self._construct_status_message()
        self.status = self._get_highest_error_level()
        self._trigger_active_problems_update()

    def update_error_log(self, message: str, exception: Optional[Exception] = None):
        """
        Logs an error and appends it to the list of current errors for display to the user.

        Params:
            message: The log message to append
            exception: exception that was thrown; None for just log the error message
        """
        if exception:
            logger.exception(message, exc_info=exception)
        else:
            logger.error(message)

        self._error_log.append(message)
        self._trigger_error_log_update()

    @property
    def status(self):
        if self._initialising:
            return STATUS.INITIALISING
        else:
            return self._status

    @status.setter
    def status(self, status_to_set):
        self._status = status_to_set
        self._trigger_status_update()

    @property
    def message(self):
        if self._initialising:
            return self.INITIALISING_MESSAGE
        else:
            return self._message

    @message.setter
    def message(self, message_to_set):
        self._message = message_to_set
        logger.info("New Status Message:")
        logger.info("{}".format(message_to_set))
        self._trigger_status_update()

    @property
    def error_log(self):
        return self._error_log_as_string()

    def _construct_status_message(self):
        message = ""
        if self.active_errors:
            message += "Errors:\n"
            for description, sources in self.active_errors.items():
                message += "- {}".format(self._problem_as_string(description, sources))
        if self.active_warnings:
            message += "Warnings:\n"
            for description, sources in self.active_warnings.items():
                message += "- {}".format(self._problem_as_string(description, sources))
        if self.active_other_problems:
            message += "Other issues:\n"
            for description, sources in self.active_other_problems.items():
                message += "- {}".format(self._problem_as_string(description, sources))

        return message

    def _error_log_as_string(self):
        log_as_string = ""
        for line in self._error_log:
            log_as_string += "{}\n".format(line)
        return log_as_string

    @staticmethod
    def _problem_as_string(description, sources):
        if len(sources) > 1:
            source_string = "(sources: {})".format(len(sources))
        else:
            source_string = "(source: {})".format(next(iter(sources)))
        return "{} {}\n".format(description, source_string)


STATUS_MANAGER = _ServerStatusManager()
