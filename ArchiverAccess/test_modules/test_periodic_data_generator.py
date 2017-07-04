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

import unittest
from datetime import datetime, timedelta

from hamcrest import *
from mock import Mock

from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.periodic_data_generator import PeriodicDataGenerator
from ArchiverAccess.test_modules.stubs import ArchiverDataStub


class TestPeriodicDataGenerator(unittest.TestCase):

    def test_GIVEN_single_initial_values_WHEN_write_values_THEN_first_data_line_is_at_start_time(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        data_generator = self._setup_data_generator(expected_start_time, [1], 10)

        result = data_generator.next()

        assert_that(result[0], is_(expected_start_time))

    def test_GIVEN_single_initial_values_WHEN_write_values_THEN_first_value_is_given_value(self):
        initial_value_pv1 = 1.23
        data_generator = self._setup_data_generator(datetime(2017, 1, 1, 1, 2, 3, 0), [initial_value_pv1], 10)

        result = data_generator.next()

        assert_that(result.values[0], is_(initial_value_pv1))

    def test_GIVEN_multiple_initial_values_WHEN_write_values_THEN_values_are_given_values(self):
        initial_value_pvs = [1.23, 3.45, 5.67]
        data_generator = self._setup_data_generator(datetime(2017, 1, 1, 1, 2, 3, 0), initial_value_pvs, 10)

        result = data_generator.next()

        assert_that(result.values, is_(initial_value_pvs))

    def test_GIVEN_initial_values_only_WHEN_write_values_THEN_time_values_are_separated_by_delta_values_are_constant(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        log_count = 10
        data_generator = self._setup_data_generator(expected_start_time, [1.23], log_count)

        results = []
        for value in data_generator:
            results.append(value)

        assert_that([x[0] for x in results], is_([expected_start_time + timedelta(seconds=delta) for delta in range(log_count + 1)]))

    def test_GIVEN_single_change_in_single_values_WHEN_write_values_THEN_value_changes_after_specified_time(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        log_count = 10
        initial_value = 1.23
        final_value = -12.24
        values = [[expected_start_time + timedelta(seconds=3.5), "pv0", final_value]]
        expected_result = [initial_value] * 4 + [final_value] * 7

        data_generator = self._setup_data_generator(expected_start_time, [initial_value], log_count, values=values)

        results = []
        for value in data_generator:
            results.append(value.values)

        assert_that([x[0] for x in results], is_(expected_result))

    def test_GIVEN_multiple_changes_in_single_value_some_more_often_than_log_frequency_some_longer_WHEN_write_values_THEN_value_changes_after_specified_time(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        log_count = 10
        initial_value = 1.23
        val1 = 6
        val2 = 23.2
        val3 = -145
        val4 = 78.5
        val5 = 34.6
        values = [
            [expected_start_time + timedelta(seconds=3.5), "pv0", val1],
            [expected_start_time + timedelta(seconds=3.6), "pv0", val2],
            [expected_start_time + timedelta(seconds=4.1), "pv0", val3],
            [expected_start_time + timedelta(seconds=6.1), "pv0", val4],
            [expected_start_time + timedelta(seconds=7), "pv0", val5]
        ]
        expected_result = [initial_value,
                           initial_value,
                           initial_value,
                           initial_value,
                           val2,
                           val3,
                           val3,
                           val5,
                           val5,
                           val5,
                           val5]

        data_generator = self._setup_data_generator(expected_start_time, [initial_value], log_count, values=values)

        results = []
        for value in data_generator:
            results.append(value.values)

        assert_that([x[0] for x in results], is_(expected_result))


    def test_GIVEN_multiple_changes_in_multiple_values_some_more_often_than_log_frequency_some_longer_WHEN_write_values_THEN_value_changes_after_specified_time(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        log_count = 10
        val0 = 4.3
        initial_values = [1.23, 8.4, val0]
        val1 = 6
        val2 = 23.2
        val3 = -145
        val4 = 78.5
        val5 = 34.6
        val6 = 13.6
        val7 = 147.6
        val8 = 1516.6
        values = [
            [expected_start_time + timedelta(seconds=3.5), "pv0", val1],
            [expected_start_time + timedelta(seconds=3.4), "pv1", val6],
            [expected_start_time + timedelta(seconds=3.6), "pv0", val2],
            [expected_start_time + timedelta(seconds=4.1), "pv0", val3],
            [expected_start_time + timedelta(seconds=6.1), "pv0", val4],
            [expected_start_time + timedelta(seconds=7), "pv0", val5],
            [expected_start_time + timedelta(seconds=7), "pv1", val7],
            [expected_start_time + timedelta(seconds=7.4), "pv1", val8]
        ]
        expected_result = [initial_values,
                           initial_values,
                           initial_values,
                           initial_values,
                           [val2, val6, val0],
                           [val3, val6, val0],
                           [val3, val6, val0],
                           [val5, val7, val0],
                           [val5, val8, val0],
                           [val5, val8, val0],
                           [val5, val8, val0]]

        data_generator = self._setup_data_generator(expected_start_time, initial_values, log_count, values=values)

        results = []
        for value in data_generator:
            results.append(value.values)

        assert_that(results, is_(expected_result))

    def test_GIVEN_string_value_WHEN_write_values_THEN_string_value_used(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        log_count = 10
        initial_value = 1.23
        final_value = "Disconnected"
        values = [[expected_start_time + timedelta(seconds=3.5), "pv0", final_value]]
        expected_result = [initial_value] * 4 + [final_value] * 7

        data_generator = self._setup_data_generator(expected_start_time, [initial_value], log_count, values=values)

        results = []
        for value in data_generator:
            results.append(value.values)

        assert_that([x[0] for x in results], is_(expected_result))

    def _setup_data_generator(self, expected_start_time, initial_pv_values, log_count, values=None, archiver_throw_exception_on_initial_values=False):
        pv_names = ["pv{0}".format(i) for i in range(len(initial_pv_values))]
        initial_pv_values_dict = {}
        for name, val  in zip(pv_names, initial_pv_values):
            initial_pv_values_dict[name] = val
        archiver_data = ArchiverDataStub(initial_pv_values_dict, values)
        if archiver_throw_exception_on_initial_values:
            archiver_data.initial_values = Mock(side_effect=ValueError())

        data_generator = PeriodicDataGenerator(archiver_data)


        return data_generator.get_generator(
            pv_names,
            ArchiveTimePeriod(expected_start_time, timedelta(seconds=1), log_count))
