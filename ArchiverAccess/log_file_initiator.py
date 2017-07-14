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


class ConfigAndDependencies(object):

    """
    config and its dependencies needed for writting a data file on pv change
    """

    def __init__(self, config, archive_data_file_creator):
        """
        Consructor
        Args:
            config(ArchiverAccess.configuration.Config): configuration
            archive_data_file_creator(ArchiverAccess.archive_data_file_creator.ArchiveDataFileCreator):
                creator of archive data files
        """

        self.config = config
        self.archive_data_file_creator = archive_data_file_creator


class LogFileInitiatorOnPVChange(object):
    """
    Initiate the writing of a log file based on the change of a PV.
    """

    def __init__(self, config_and_dependencies, archive_data_source, search_for_change_from):
        """

        Args:
            config_and_dependencies(list[ConfigAndDependencies]): list of configs along with their needed dependencies
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource): data source
            search_for_change_from: time from which to search for changes in the pv
        """

        self._config_and_dependencies = config_and_dependencies
        self._archive_data_source = archive_data_source
        self._trigger_pvs = [cad.config.trigger_pv for cad in config_and_dependencies]

        initial_data_values = archive_data_source.initial_archiver_data_values(
            self._trigger_pvs, search_for_change_from)
        self._last_sample_id = self._archive_data_source.sample_id(search_for_change_from)

        self._logging_started = []
        for initial_data_value in initial_data_values:
            if self._value_is_logging_on(initial_data_value.value):
                self._logging_started.append(initial_data_value.sample_time)
            else:
                self._logging_started.append(None)

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

            logging_start_time = self._logging_started[pv_index]
            if logging_start_time is None:
                if self._value_is_logging_on(value):
                    self._logging_started[pv_index] = timestamp
            else:
                if not self._value_is_logging_on(value):
                    logging_period = timedelta(seconds=self._config_and_dependencies[pv_index].config.logging_period)
                    time_period = ArchiveTimePeriod(logging_start_time, logging_period, finish_time=timestamp)
                    self._config_and_dependencies[pv_index].archive_data_file_creator.write(time_period)
                    self._logging_started[pv_index] = None

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
