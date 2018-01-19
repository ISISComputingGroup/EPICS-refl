# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Module for initiator for log file creation.
"""
from datetime import timedelta, datetime

from ArchiverAccess.archive_data_file_creator import DataFileCreationError, DataFileCreatorFactory
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from server_common.utilities import print_and_log, SEVERITY

# The delay between the current time and what we think should have been archived. This is so if nothing is archived
# the continous logger will still produce values but will still catch values coming through the system. The values
# are written every 60s so this is ample time to get the last value
SAMPLING_BEHIND_REAL_TIME = timedelta(seconds=90)


class LogFileInitiatorOnPVChange(object):
    """
    Initiate the writing of a log file based on the change of a PV.
    """

    def __init__(self, configs, archive_data_source, time_last_active,
                 get_current_time_fn=datetime.utcnow, data_file_creator_factory=DataFileCreatorFactory()):
        """

        Args:
            configs(list[ArchiverAccess.archive_access_configuration.ArchiveAccessConfig]):
                list of configs
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource):
                data source
            time_last_active(ArchiverAccess.time_last_active.TimeLastActive):
                provider for the time from which to search for changes in the logging pv
            get_current_time_fn: function to get the current time
            data_file_creator_factory(ArchiverAccess.archive_data_file_creator.DataFileCreatorFactory):
                factory to create data file creator objects
        """
        self._get_current_time_fn = get_current_time_fn
        self._archive_data_source = archive_data_source
        self._trigger_pvs = [config.trigger_pv for config in configs]
        self._time_last_active = time_last_active
        search_for_change_from, self._last_sample_id_for_time = time_last_active.get()
        initial_data_values = archive_data_source.initial_archiver_data_values(self._trigger_pvs,
                                                                               search_for_change_from)
        self._last_sample_time = search_for_change_from

        self._loggers_for_pvs = []
        for config, initial_data_value in zip(configs, initial_data_values):
            cont_logger = ContinualLogger(config, self._archive_data_source, data_file_creator_factory)
            end_logger = WriteOnLoggingEndLogger(config, self._archive_data_source, data_file_creator_factory)
            loggers = (cont_logger, end_logger)

            if self._value_is_logging_on(initial_data_value.value):
                [logger.logging_switched_on(initial_data_value.sample_time) for logger in loggers]

            self._loggers_for_pvs.append(loggers)

    def check_initiated(self):
        """
        Check whether an initiation event has occurred.

        If it has the archive data file needs creating and writen.

        Returns:

        """
        latest_sample_time, self._last_sample_id_for_time = \
            self._archive_data_source.get_latest_sample_time(self._last_sample_id_for_time)

        current_time_with_delay = self._get_current_time_fn() - SAMPLING_BEHIND_REAL_TIME
        current_sample_time = max(latest_sample_time, current_time_with_delay, self._last_sample_time)
        changes = self._archive_data_source.logging_changes_for_sample_id_generator(
            self._trigger_pvs, self._last_sample_time, current_sample_time)
        self._last_sample_time = current_sample_time

        for timestamp, pv_index, value in changes:
            if self._value_is_logging_on(value):
                print_and_log("Continual logging started for {0} at {1}".format(self._trigger_pvs[pv_index], timestamp),
                              src="ArchiverAccess")
                for logger in self._loggers_for_pvs[pv_index]:
                    logger.logging_switched_on(timestamp)
            else:
                print_and_log("Logging stopped for {0} at {1}".format(self._trigger_pvs[pv_index], timestamp),
                              src="ArchiverAccess")
                for logger in self._loggers_for_pvs[pv_index]:
                    logger.logging_switched_off(timestamp)

        for loggers_for_pv in self._loggers_for_pvs:
            for logger in loggers_for_pv:
                logger.post_changes(current_sample_time)

        self._time_last_active.set(current_sample_time, self._last_sample_id_for_time)

    def _value_is_logging_on(self, value):
        """
        Args:
            value: value is to check

        Returns: true if the value represents logging is on; False otherwise

        """
        try:
            return int(value) == 1
        except (TypeError, ValueError):
            # main case is pv is disconnected
            return False


class ContinualLogger(object):
    """
    A logger that will write the data to the file every period.
    """

    def __init__(self, config, archive_data_source, data_file_creator_factory):
        """
        Initializer.
        Args:
            config(ArchiverAccess.archive_access_configuration.ArchiveAccessConfig):
                configuration for this logging set
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource):
                data source from the archive
            data_file_creator_factory: factor to allow creation of data files
        """
        self._archive_data_source = archive_data_source
        self._config = config
        self._archive_data_file_creator = data_file_creator_factory.create(config, archive_data_source,
                                                                           config.continuous_logging_filename_template)
        self._last_write_time = None

    def logging_switched_on(self, timestamp):
        """
        Do the action for when the logging was switched on so write the log file header.
        Args:
            timestamp: time at which the logging was started

        """
        continual_logging_last_write = self._last_write_time
        if continual_logging_last_write is None:
            # not continually logging at the moment
            self._last_write_time = timestamp
            try:
                self._archive_data_file_creator.write_file_header(timestamp)
            except DataFileCreationError as e:
                print_and_log("{}".format(e), severity=SEVERITY.MAJOR, src="ArchiverAccess")

    def logging_switched_off(self, timestamp):
        """
        Do the action for when the logging was switched off so write the rest of the lines to the file.
        Args:
            timestamp: time logging stopped

        """
        if self._last_write_time is not None:

            self._write_data_lines_for_period(timestamp)
            self._last_write_time = None
            try:
                self._archive_data_file_creator.finish_log_file()
            except DataFileCreationError as e:
                print_and_log("{}".format(e), severity=SEVERITY.MAJOR, src="ArchiverAccess")

    def post_changes(self, timestamp):
        """
        Do the action when all changes for the period are processed, in this case write data line to open log files
        Args:
            timestamp: time to which changes have been considered

        """
        if self._last_write_time is not None:
            self._write_data_lines_for_period(timestamp)
            self._last_write_time = timestamp

    def _write_data_lines_for_period(self, timestamp):
        """
        Write lines to datafile from last write to timestamp
        Args:
            timestamp: time to write data line to

        """
        logging_start_time = self._last_write_time
        logging_period_provider = self._config.logging_period_provider
        logging_period = logging_period_provider.get_logging_period(self._archive_data_source, logging_start_time)
        time_period = ArchiveTimePeriod(logging_start_time, logging_period, finish_time=timestamp)
        try:
            archive_data_file_creator = self._archive_data_file_creator
            archive_data_file_creator.write_data_lines(time_period)
        except DataFileCreationError as e:
            print_and_log("{}".format(e), severity=SEVERITY.MAJOR, src="ArchiverAccess")


class WriteOnLoggingEndLogger(object):
    """
    Logger which writes a file when logging ends
    """

    def __init__(self, config, archive_data_source, data_file_creator_factory):
        """
        Initializer.
        Args:
            config(ArchiverAccess.archive_access_configuration.ArchiveAccessConfig):
                configuration for this logging set
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource):
                data source from the archive
            data_file_creator_factory: factor to allow creation of data files
        """
        self._logging_started = None
        self._archive_data_source = archive_data_source
        self._config = config
        self._archive_data_file_creator = data_file_creator_factory.create(config, archive_data_source,
                                                                           config.on_end_logging_filename_template)

    def logging_switched_on(self, timestamp):
        """
        Do the action for when the logging was switched on which is to store the time.
        Args:
            timestamp: time logging was switched on
        """
        if self._logging_started is None:
            self._logging_started = timestamp

    def logging_switched_off(self, timestamp):
        """
        Do the action for when the logging was switched off which is to write the complete file.
        Args:
            timestamp: time when logging was switched off
        """
        if self._logging_started is None:
            return

        logging_period_provider = self._config.logging_period_provider
        logging_period = logging_period_provider.get_logging_period(self._archive_data_source, self._logging_started)
        time_period = ArchiveTimePeriod(self._logging_started, logging_period, finish_time=timestamp)
        try:
            self._archive_data_file_creator.write_complete_file(time_period)
        except DataFileCreationError as e:
            print_and_log("{}".format(e), severity=SEVERITY.MAJOR, src="ArchiverAccess")
        self._logging_started = None

    def post_changes(self, timestamp):
        """
        This does nothing since the log file is only written to at the end.

        Args:
            timestamp: time to write data line to
        """
        pass
