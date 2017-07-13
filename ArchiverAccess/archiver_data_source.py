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
Module for defining a data source from the archiver
"""

from datetime import timedelta, datetime

from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from server_common.mysql_abstraction_layer import SQLAbstraction

ERROR_PREFIX = "ERROR: "
VALUE_WHEN_ERROR_ON_RETRIEVAL = ERROR_PREFIX + "Data value can not be retrieved"
"""Error to put in a cell if the data can not be retrieved"""


class ArchiverDataValue:
    """
    A value from the archiver database
    """
    def __init__(self, data_base_query_list=None, retrieval_error=False):
        """
        Constructor
        Args:
            data_base_query_list: list from a database query; if None all values are None (except retrieval error)
            retrieval_error: true if there was a problem retrieving the value; false otherwise
        """
        if data_base_query_list is not None:
            self.severity_id, self.status_id, self.num_val, self.float_val, self.str_val, self.array_val, \
                self.sample_time = data_base_query_list
        else:
            self.severity_id = self.status_id = self.num_val = self.float_val = self.array_val = self.str_val = None

        self.retrieval_error = retrieval_error

    @property
    def value(self):
        """

        Returns: the first non None value from the database line
        (if there is a retrieval error returns the error string for that)

        """
        if self.retrieval_error:
            return VALUE_WHEN_ERROR_ON_RETRIEVAL
        if self.num_val is not None:
            return self.num_val
        if self.float_val is not None:
            return self.float_val
        if self.str_val is not None:
            return self.str_val
        return self.array_val

    def __str__(self):
        return str(self.value)

    def get_as_array(self):
        """

        Returns: values as they would appear from the database

        """
        return [self.severity_id, self.status_id, self.num_val, self.float_val, self.str_val, self.array_val,
                self.sample_time]

INITIAL_VALUES_QUERY = """
    SELECT severity_id, status_id, num_val, float_val, str_val, array_val, smpl_time
      FROM archive.sample 
     WHERE sample_id = (
        SELECT max(s.sample_id)
          FROM archive.sample s
         WHERE channel_id = (
                SELECT channel_id
                  FROM archive.channel
                 WHERE name = %s)
           AND s.smpl_time <= %s
     )
"""
""" SQL Query to return the values at a specific time by lookking for the latest sampled value for the 
pv before the given time"""

GET_CHANGES_QUERY_FOR_ALL_TIME = """
    SELECT c.name, s.smpl_time, s.severity_id, s.status_id, s.num_val, s.float_val, s.str_val, s.array_val
      FROM archive.sample s
      JOIN archive.channel c ON c.channel_id = s.channel_id
    
     WHERE s.channel_id in (
            SELECT channel_id
              FROM archive.channel c
             WHERE name in ({0}))
"""

GET_CHANGES_QUERY = GET_CHANGES_QUERY_FOR_ALL_TIME + """

      AND s.smpl_time > %s
      AND s.smpl_time <= %s
"""
"""SQL query to get a list of changes after a given time for certain pvs"""

GET_CHANGES_QUERY_FOR_SAMPLE_ID_PERIOD = GET_CHANGES_QUERY_FOR_ALL_TIME + """

      AND s.sample_id > %s
      AND s.sample_id <= %s
"""
"""SQL query to get a list of changes after a given time for certain pvs"""


GET_SAMPLE_ID_NOW = """
        SELECT max(s.sample_id)
          FROM archive.sample s
"""

GET_SAMPLE_ID = GET_SAMPLE_ID_NOW + """
         WHERE s.smpl_time <= %s
"""


class ArchiverDataSource(object):
    """
    Data source for the archiver data.
    """

    def __init__(self, sql_abstraction_layer):
        """
        Constructor

        Args:
            sql_abstraction_layer(SQLAbstraction): sql abstraction allowing calling of database queries
        """
        self._sql_abstraction_layer = sql_abstraction_layer

    def initial_archiver_data_values(self, pv_names, time):
        """

        Args:
            pv_names: tuple of pv names that will be accessed for the period of time
            time: time at which to get values for pvs

        :return: initial values for the pvs (i.e. the value at the start time)
        """
        initial_values = []
        for pv_name in pv_names:
            result = self._sql_abstraction_layer.query(INITIAL_VALUES_QUERY, (pv_name, time))
            if len(result) == 1:
                initial_values.append(ArchiverDataValue(result[0]))
            elif len(result) == 0:
                initial_values.append(ArchiverDataValue())
            else:
                initial_values.append(ArchiverDataValue(retrieval_error=True))
        return initial_values

    def initial_values(self, pv_names, time):
        """

        Args:
            pv_names: tuple of pv names that will be accessed for the period of time
            time: time at which to get values for pvs

        :return: initial values for the pvs (i.e. the value at the start time)
        """
        return [archiver_data_value.value for archiver_data_value in self.initial_archiver_data_values(pv_names, time)]

    def changes_generator(self, pv_names, time_period):
        """
        Generator of changes in pv values with dates

        Args:
            pv_names: tuple of pv names to look for changes in
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period to query for

        Returns:
            generator which gives tuple of timestamp, pv index and new value

        """
        query_with_correct_number_of_bound_ins = GET_CHANGES_QUERY.format(", ".join(["%s"] * len(pv_names)))
        changes_cursor = self._sql_abstraction_layer.query_returning_cursor(
            query_with_correct_number_of_bound_ins, pv_names + (time_period.start_time, time_period.end_time))
        for values in self._changes_generator(pv_names, changes_cursor):
            yield values

    def sample_id(self, time=None):
        """
        Get the largest sample id taken before a given time

        Args:
            time: time at which to get the sample id

        :return: sample id or 0 if there is no sample id before the given time
        """
        if time is not None:
            sample_id_result = self._sql_abstraction_layer.query(GET_SAMPLE_ID, (time,))
        else:
            sample_id_result = self._sql_abstraction_layer.query(GET_SAMPLE_ID_NOW)
        if len(sample_id_result) == 1:
            sample_id = sample_id_result[0]
        else:
            sample_id = 0

        return sample_id

    def logging_changes_for_sample_id_generator(self, pv_names, from_sample_id, to_sample_id):
        """
        Generator of changes in pv values between sample ids

        Args:
            pv_names: tuple of pv names to look for changes in
            from_sample_id: lowest sample id (excluded)
            to_sample_id: highest sample id (included)

        Returns:
            generator which gives tuple of timestamp, pv index and new value

        """
        sql_in_binding = self._sql_abstraction_layer.generate_in_binding(len(pv_names))
        query_with_correct_number_of_bound_ins = GET_CHANGES_QUERY_FOR_SAMPLE_ID_PERIOD.format(sql_in_binding)
        changes_cursor = self._sql_abstraction_layer.query_returning_cursor(
            query_with_correct_number_of_bound_ins,
            pv_names + (from_sample_id, to_sample_id))
        for values in self._changes_generator(pv_names, changes_cursor):
            yield values

    def _changes_generator(self, pv_names, changes_cursor):
        for database_return in changes_cursor:
            value = ArchiverDataValue(database_return[2:])
            channel_name = database_return[0]
            index = pv_names.index(channel_name)
            time_stamp = database_return[1]
            yield(time_stamp, index, value.value)


if __name__ == "__main__":
    ads = ArchiverDataSource(SQLAbstraction("archive", "report", "$report"))
    start_time = datetime(2020, 06, 16, 0, 0, 0)
    pv_values = ('TE:NDW1798:TPG26X_01:2:ERROR.VAL', 'TE:NDW1798:EUROTHRM_01:A01:TEMP.VAL')
    period = ArchiveTimePeriod(start_time, timedelta(days=365), 10)

    for val in ads.initial_values(pv_values, start_time):
        print str(val)

    for val in ads.changes_generator(pv_values, period):
        print str(val)
