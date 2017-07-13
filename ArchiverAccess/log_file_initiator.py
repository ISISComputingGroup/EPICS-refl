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

from datetime import timedelta

from ArchiverAccess.archive_time_period import ArchiveTimePeriod


class LogFileInitiatorOnPVChange(object):
    """
    Initiate the writing of a log file based on the change of a PV.
    """

    def __init__(self, config, archive_data_source, archive_data_file_creator):
        """

        Args:
            config(ArchiverAccess.configuration.Config): configuration
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource): data source
            archive_data_file_creator(ArchiverAccess.archive_data_file_creator.ArchiveDataFileCreator):
                creator of archive data files
        """
        self._config = config
        self._archive_data_source = archive_data_source
        self._archive_data_file_creator = archive_data_file_creator
        self._trigger_pvs = [config.trigger_pv]

        self._initial_data = archive_data_source.initial_archiver_data_values(
            self._trigger_pvs, config.create_logs_from())
        self._last_sample_id = self._archive_data_source.sample_id(config.create_logs_from())

        if self._value_is_logging_on(self._initial_data[0].value):
            self._logging_started = self._initial_data[0].sample_time
        else:
            self._logging_started = None

        self._logging_period = timedelta(seconds=self._config.logging_period)

    def check_write(self):
        """
        Check whether a archive data file needs creating and write it if needed.

        Returns:

        """

        current_sample_id = self._archive_data_source.sample_id()
        changes = self._archive_data_source.logging_changes_for_sample_id_generator(
            self._trigger_pvs, self._last_sample_id, current_sample_id)
        self._last_sample_id = current_sample_id

        for timestamp, pv_index, value in changes:

            if self._logging_started is None:
                if self._value_is_logging_on(value):
                    self._logging_started = timestamp
            else:
                if not self._value_is_logging_on(value):
                    time_period = ArchiveTimePeriod(self._logging_started, self._logging_period, finish_time=timestamp)
                    self._archive_data_file_creator.write(time_period)
                    self._logging_started = None

    def _value_is_logging_on(self, value):
        """
        Args:
            value: value is to check

        Returns: true if the value represents logging is on; False otherwise

        """
        try:
            return int(value) == 1
        except ValueError:
            # main case is pv is disconnected
            return False
