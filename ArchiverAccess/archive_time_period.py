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
Module for defining a time period for the archive access
"""

from datetime import datetime

from ArchiverAccess.utilities import truncate


class ArchiveTimePeriod(object):
    """
    A time period.
    """

    def __init__(self, start_time, delta, point_count=None, finish_time=None):
        """
        Construct a time period.

        Args:
            start_time(datetime): the start time of the period (this is rounded down to the nearest 10th of a second)
            delta: the delta of each point within a period
            point_count: the number of points in the period
            finish_time: the end time is the last value that is logged before this time
        """
        nearest_10th_second = truncate(start_time.microsecond, -5)
        self.start_time = start_time.replace(microsecond=nearest_10th_second)
        self.delta = delta
        if point_count is None:
            self.point_count = int((finish_time - self.start_time).total_seconds() // self.delta.total_seconds() + 1)
        else:
            self.point_count = point_count

        number_of_deltas = self.point_count - 1
        self.end_time = self.start_time + number_of_deltas * self.delta

    def get_time_after(self, periods_count):
        """

        Args:
            periods_count: number of deltas that have passed in the period

        Returns: the current ime in the period

        """
        return self.start_time + self.delta * periods_count

    def __repr__(self):
        return "From {0} to {1} in periods of {2}s".format(self.start_time, self.end_time, self.delta.total_seconds())
