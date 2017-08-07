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

from datetime import datetime, timedelta
from unittest import TestCase

from hamcrest import *
from ArchiverAccess.archive_time_period import ArchiveTimePeriod


class TestConfiguration(TestCase):

    def test_GIVEN_start_period_and_points_WHEN_get_all_THEN_correct(self):
        expected_start = datetime(2016, 1, 2, 3, 4, 5)
        expected_delta = timedelta(seconds=1)
        expected_point_count = 100
        expected_end_time = datetime(2016, 1, 2, 3, 5, 44)

        time_period = ArchiveTimePeriod(expected_start, expected_delta, expected_point_count)

        assert_that(time_period.start_time, is_(expected_start))
        assert_that(time_period.delta, is_(expected_delta))
        assert_that(time_period.point_count, is_(expected_point_count))
        assert_that(time_period.end_time, is_(expected_end_time))

    def test_GIVEN_start_delta_and_1_points_WHEN_get_all_THEN_correct(self):
        expected_start = datetime(2016, 1, 2, 3, 4, 5)
        expected_delta = timedelta(seconds=1)
        expected_point_count = 1
        expected_end_time = expected_start

        time_period = ArchiveTimePeriod(expected_start, expected_delta, expected_point_count)

        assert_that(time_period.start_time, is_(expected_start))
        assert_that(time_period.delta, is_(expected_delta))
        assert_that(time_period.point_count, is_(expected_point_count))
        assert_that(time_period.end_time, is_(expected_end_time))

    def test_GIVEN_start_with_micro_seconds_WHEN_get_all_THEN_start_time_truncated_to_nearest_whole_tenth_of_a_second(self):
        start = datetime(2016, 1, 2, 3, 4, 5, 4)
        expected_start = datetime(2016, 1, 2, 3, 4, 5)

        time_period = ArchiveTimePeriod(start, timedelta(minutes=1), 0)

        assert_that(time_period.start_time, is_(expected_start))

    def test_GIVEN_start_with_multiple_micro_seconds_WHEN_get_all_THEN_start_time_truncated_to_nearest_whole_tenth_of_a_second(
            self):
        start = datetime(2016, 1, 2, 3, 4, 5, 250000)
        expected_start = datetime(2016, 1, 2, 3, 4, 5, 200000)

        time_period = ArchiveTimePeriod(start, timedelta(minutes=1), 0)

        assert_that(time_period.start_time, is_(expected_start))

    def test_GIVEN_start_delta_and_end_which_is_a_multiple_of_delta_only_2_WHEN_get_all_THEN_points_is_correct_and_so_is_end(self):
        expected_start = datetime(2016, 1, 2, 3, 4, 5)
        expected_delta = timedelta(seconds=1)
        expected_point_count = 2
        expected_end_time = datetime(2016, 1, 2, 3, 4, 6)

        time_period = ArchiveTimePeriod(expected_start, expected_delta, finish_time=expected_end_time)

        assert_that(time_period.start_time, is_(expected_start))
        assert_that(time_period.delta, is_(expected_delta))
        assert_that(time_period.point_count, is_(expected_point_count))
        assert_that(time_period.end_time, is_(expected_end_time))

    def test_GIVEN_start_delta_and_end_which_is_a_multiple_of_delta_WHEN_get_all_THEN_points_is_correct_and_so_is_end(self):
        expected_start = datetime(2016, 1, 2, 3, 4, 5)
        expected_delta = timedelta(seconds=1)
        expected_point_count = 10
        expected_end_time = datetime(2016, 1, 2, 3, 4, 14)

        time_period = ArchiveTimePeriod(expected_start, expected_delta, finish_time=expected_end_time)

        assert_that(time_period.start_time, is_(expected_start))
        assert_that(time_period.delta, is_(expected_delta))
        assert_that(time_period.point_count, is_(expected_point_count))
        assert_that(time_period.end_time, is_(expected_end_time))

    def test_GIVEN_start_delta_and_end_which_is_not_a_multiple_of_delta_WHEN_get_all_THEN_points_is_correct_and_so_is_end(self):
        expected_start = datetime(2016, 1, 2, 3, 4, 5)
        expected_delta = timedelta(seconds=1)
        expected_point_count = 10
        end_time = datetime(2016, 1, 2, 3, 4, 14, 1000)
        expected_end_time = datetime(2016, 1, 2, 3, 4, 14)

        time_period = ArchiveTimePeriod(expected_start, expected_delta, finish_time=end_time)

        assert_that(time_period.start_time, is_(expected_start))
        assert_that(time_period.delta, is_(expected_delta))
        assert_that(time_period.point_count, is_(expected_point_count))
        assert_that(time_period.end_time, is_(expected_end_time))
