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
Module to read and write when logs were last written
"""

import os
from datetime import datetime, timedelta

from ArchiverAccess.archive_access_configuration import DEFAULT_LOG_PATH
from server_common.utilities import print_and_log, SEVERITY

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
"""Format to write time to file in"""

TIME_LAST_ACTIVE_HEADER = "# File containing two line, 1. time the logger last wrote to file and " \
                          "maximum number of days that the archiver access should go back to generate log files"
"""Header for the last active file """

TIME_LAST_ACTIVE_FILENAME = os.path.join(DEFAULT_LOG_PATH, "LOG_last_active_time")
"""File name for the last active file"""

DEFAULT_DELTA = 1
"""If there is an error this is the default delta"""


class TimeLastActive(object):
    """
    Allow Getting and Settting of the time last active log was written. This is stored in a file.
    """
    def __init__(self, file_cls=file, time_now_fn=datetime.utcnow):
        """
        Constructor
        Args:
            file_cls: file class tp ise
            time_now_fn: function to return the current time
        """
        self._file = file_cls
        self._time_now_fn = time_now_fn

    def get(self):
        """
        This will return the date in the last active file unless it is before before now by a delta in which case it
         will return now - delta. The delta is the third line in the log file in days. If the file is not readable
         then the time now - 1 day is returned.

        Returns: the last time that this service was active

        """
        time_last_active, sample_id = self._get_last_active()
        print_and_log("Last active: {0} ({1})".format(time_last_active.isoformat(), sample_id), src="ArchiverAccess")
        return time_last_active, sample_id

    def _get_last_active(self):
        """

        Returns: time last active

        """
        time_now = self._time_now_fn()
        sample_id = 0
        try:
            with self._file(TIME_LAST_ACTIVE_FILENAME, mode="r") as time_last_active_file:
                time_last_active_file.readline()
                last_active_time = datetime.strptime(time_last_active_file.readline().strip(), TIME_FORMAT)
                max_delta = int(time_last_active_file.readline().strip())
                sample_id = int(time_last_active_file.readline().strip())
        except (ValueError, TypeError, IOError) as ex:
            print_and_log("Failed to read last active file error '{0}'".format(ex),
                          severity=SEVERITY.MINOR, src="ArchiverAccess")
            return time_now - timedelta(days=DEFAULT_DELTA), sample_id
        if max_delta < 0:
            max_delta = DEFAULT_DELTA
        earliest_time = time_now - timedelta(days=max_delta)
        if earliest_time > last_active_time:
            return earliest_time, sample_id
        return last_active_time, sample_id

    def set(self, last_active_time, last_sample_id, delta=DEFAULT_DELTA):
        """
        Write a last active time with a delta to the file
        Args:
            last_active_time(datetime): the time to write
            last_sample_id: sample id last read from the database
            delta: the furthest time back from this moment in days that the last active time should be reported

        Returns:

        """
        try:
            with self._file(TIME_LAST_ACTIVE_FILENAME, mode="w") as time_last_active_file:
                time_last_active_file.write("{0}\n".format(TIME_LAST_ACTIVE_HEADER))
                time_last_active_file.write("{0}\n".format(last_active_time.strftime(TIME_FORMAT)))
                time_last_active_file.write("{0}\n".format(delta))
                time_last_active_file.write("{0}\n".format(last_sample_id))
        except (ValueError, TypeError, IOError)as err:
            print_and_log("Error writing last activity file: '{0}'".format(err))
