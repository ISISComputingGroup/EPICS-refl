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

from ArchiverAccess.archive_data_file_creator import DataFileCreationError
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataValue
from ArchiverAccess.archive_access_configuration import ArchiveAccessConfigBuilder
from ArchiverAccess.log_file_initiator import LogFileInitiatorOnPVChange, SAMPLING_BEHIND_REAL_TIME
from ArchiverAccess.test_modules.stubs import ArchiverDataStub


class TestLogFileInitiatorForContinousLogging(unittest.TestCase):
    def test_GIVEN_config_with_pv_WHEN_logging_pv_has_changed_0_to_1_THEN_log_file_created(self):
            # logging pv changes to 1 then back to 0
            expected_logging_start = datetime(2017, 1, 1, 1, 1, 2)

            data_changes = [[(expected_logging_start, 0, 1)]]
            archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[0], data_changes=data_changes,
                                                                      logging_start_times=[datetime(2017, 1, 1, 1, 1, 1)])
            write_file_header_mock = Mock()
            log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, write_file_header_mock=write_file_header_mock)

            log_file_initiator.check_initiated()

            write_file_header_mock.assert_called_once_with(expected_logging_start)

    def test_GIVEN_config_with_pv_WHEN_logging_pv_has_swicthed_off_in_changes_THEN_log_file_body_written_and_file_made_readonly(self):
            log_period_in_second = 1
            expected_period = timedelta(seconds=log_period_in_second)
            # logging pv changes to 1 then back to 0
            expected_logging_start = datetime(2017, 1, 1, 1, 1, 2)
            expected_logging_stop = datetime(2017, 1, 1, 1, 2, 2)
            data_changes = [[(expected_logging_start, 0, 1),
                             (expected_logging_stop, 0, 0)]]
            archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[0], data_changes=data_changes,
                                                                      logging_start_times=[datetime(2017, 1, 1, 1, 1, 1)])
            write_data_lines_mock = Mock()
            finished_log_file_mock = Mock()
            log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, write_data_lines_mock=write_data_lines_mock, finish_log_file_mock=finished_log_file_mock)

            log_file_initiator.check_initiated()

            write_data_lines_mock.assert_called_once_with(ArchiveTimePeriod(expected_logging_start, expected_period, finish_time=expected_logging_stop))
            finished_log_file_mock.assert_called_once()

    def test_GIVEN_config_with_pv_WHEN_logging_switches_on_in_changes_period_THEN_log_file_body_written_to_end_of_period_finish_not_written(self):
            log_period_in_second = 1
            expected_period = timedelta(seconds=log_period_in_second)
            expected_end_time = datetime(2017, 1, 1, 1, 1, 2)

            # logging pv changes to 1 then back to 0
            expected_logging_start = datetime(2017, 1, 1, 1, 1, 1)
            data_changes = [[(expected_logging_start, 0, 1)]]
            archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[0], data_changes=data_changes,
                                                                      logging_start_times=[datetime(2017, 1, 1, 1, 1, 1)], sample_times=[expected_end_time])
            write_data_lines_mock = Mock()
            finished_log_file_mock = Mock()
            log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, write_data_lines_mock=write_data_lines_mock, finish_log_file_mock=finished_log_file_mock)

            log_file_initiator.check_initiated()

            write_data_lines_mock.assert_called_once_with(ArchiveTimePeriod(expected_logging_start, expected_period, finish_time=expected_end_time))
            finished_log_file_mock.assert_not_called()

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_twice_from_1_to_0_THEN_two_continual_log_files_created(self):
        log_period_in_second = 1
        expected_period = timedelta(seconds=log_period_in_second)
        expected_logging_start1 = datetime(2017, 1, 1, 1, 1, 1)
        data_changes = [[(datetime(2017, 1, 1, 1, 1, 2), 0, 0),
                        (datetime(2017, 1, 1, 1, 2, 2), 0, 1),
                        (datetime(2017, 1, 1, 1, 3, 2), 0, 0)]]
        write_data_lines_mock = Mock()
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], data_changes=data_changes, logging_start_times=[expected_logging_start1],)
        expected_logging_stop_time1 = datetime(2017, 1, 1, 1, 1, 2)
        expected_logging_start_time2 = datetime(2017, 1, 1, 1, 2, 2)
        expected_logging_stop_time2 = datetime(2017, 1, 1, 1, 3, 2)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second], write_data_lines_mock=write_data_lines_mock)

        log_file_initiator.check_initiated()

        arg_list = write_data_lines_mock.call_args_list
        logging_time_period1 = arg_list[0][0][0]
        self.assert_logging_period_correct(logging_time_period1, expected_logging_start1, expected_logging_stop_time1,
                                           expected_period)

        logging_time_period2 = arg_list[1][0][0]
        self.assert_logging_period_correct(logging_time_period2, expected_logging_start_time2,
                                           expected_logging_stop_time2,
                                           expected_period)

    def assert_logging_period_correct(self, logging_time_period, expected_logging_start, expected_logging_stop_time,
                                      expected_period):
        assert_that(logging_time_period.delta, is_(expected_period), "Delta")
        assert_that(logging_time_period.start_time, is_(expected_logging_start), "Start time")
        assert_that(logging_time_period.end_time, is_(expected_logging_stop_time), "End time")

    def test_GIVEN_config_with_pv_WHEN_logging_pv_is_initially_at_1_THEN_log_file_header_created(self):
            expected_logging_start = datetime(2017, 1, 1, 1, 1, 2)
            initial_values = [1]
            archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=initial_values,
                                                                      logging_start_times=[expected_logging_start])
            write_file_header_mock = Mock()
            log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, write_file_header_mock=write_file_header_mock)

            log_file_initiator.check_initiated()

            write_file_header_mock.assert_called_once_with(expected_logging_start)


class TestLogFileInitiator(unittest.TestCase):

    def test_GIVEN_config_with_pv_WHEN_get_data_THEN_correct_sample_times_asked_for(self):
        sample_times = [datetime(2001, 2, 3, 4, 5, 36)]
        time_last_active = datetime(2001, 2, 3, 4, 5, 6)
        sample_id_last_active = 10
        archive_data_source = DataSourceMother.set_up_data_source(sample_times=sample_times)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, time_last_actived=time_last_active, sample_id_last_active=sample_id_last_active)

        log_file_initiator.check_initiated()

        assert_that(archive_data_source.from_sample_time, is_([time_last_active]))
        assert_that(archive_data_source.to_sample_time, is_([sample_times[0]]))
        assert_that(archive_data_source.from_sample_id, is_([sample_id_last_active]))

    def test_GIVEN_config_with_pv_WHEN_check_write_twice_THEN_consecutive_sample_times_are_used(self):
        sample_ids = [90, 91]
        sample_id_last_active = 10
        time_last_active = datetime(2001, 2, 3, 4, 5, 6)
        sample_times = [datetime(2001, 2, 3, 4, 5, 36), datetime(2001, 2, 3, 4, 6, 6)]
        archive_data_source = DataSourceMother.set_up_data_source(sample_times=sample_times, data_changes=[[], []], sample_ids=sample_ids)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, time_last_actived=time_last_active, sample_id_last_active=sample_id_last_active)

        log_file_initiator.check_initiated()
        log_file_initiator.check_initiated()

        assert_that(archive_data_source.from_sample_time, is_([time_last_active, sample_times[0]]))
        assert_that(archive_data_source.to_sample_time, is_([sample_times[0], sample_times[1]]))
        assert_that(archive_data_source.from_sample_id, is_([sample_id_last_active, sample_ids[0]]))

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_from_1_to_0_THEN_log_file_created(self):
        log_period_in_second = 1
        expected_period = timedelta(seconds=log_period_in_second)
        expected_logging_start = datetime(2017, 1, 1, 1, 1, 1)
        logging_stop_time = datetime(2017, 1, 1, 1, 1, 2)
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], final_pv_value=0)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second])

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_called_once()
        logging_time_period = self.log_file_creators[0].write_complete_file.call_args[0][0]
        assert_that(logging_time_period.delta, is_(expected_period))
        assert_that(logging_time_period.start_time, is_(expected_logging_start))
        assert_that(logging_time_period.end_time, is_(logging_stop_time))


    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_0_to_X_THEN_log_file_not_created(self):
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[0], final_pv_value=1)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source)

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_not_called()

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_0_to_0_THEN_log_file_not_created(self):
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[0], final_pv_value=0)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source)

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_not_called()

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_1_to_disconnect_THEN_log_file_created(self):
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], final_pv_value="disconnect")
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source)

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_called()

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_disconnected_to_0_THEN_log_file_not_created(self):
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=["disconnect"], final_pv_value=1)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source)

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_not_called()


    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_twice_from_1_to_0_THEN_log_file_created(self):
        log_period_in_second = 1
        expected_period = timedelta(seconds=log_period_in_second)
        expected_logging_start1 = datetime(2017, 1, 1, 1, 1, 1)
        data_changes = [[(datetime(2017, 1, 1, 1, 1, 2), 0, 0),
                        (datetime(2017, 1, 1, 1, 2, 2), 0, 1),
                        (datetime(2017, 1, 1, 1, 3, 2), 0, 0)]]
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], data_changes=data_changes, logging_start_times=[expected_logging_start1])
        expected_logging_stop_time1 = datetime(2017, 1, 1, 1, 1, 2)
        expected_logging_start_time2 = datetime(2017, 1, 1, 1, 2, 2)
        expected_logging_stop_time2 = datetime(2017, 1, 1, 1, 3, 2)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second])

        log_file_initiator.check_initiated()

        arg_list = self.log_file_creators[0].write_complete_file.call_args_list
        logging_time_period1 = arg_list[0][0][0]
        assert_that(logging_time_period1.delta, is_(expected_period))
        assert_that(logging_time_period1.start_time, is_(expected_logging_start1))
        assert_that(logging_time_period1.end_time, is_(expected_logging_stop_time1))

        logging_time_period2 = arg_list[1][0][0]
        assert_that(logging_time_period2.delta, is_(expected_period))
        assert_that(logging_time_period2.start_time, is_(expected_logging_start_time2))
        assert_that(logging_time_period2.end_time, is_(expected_logging_stop_time2))

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_twice_from_1_to_0_over_two_different_write_checks_THEN_two_log_files_created(self):
        log_period_in_second = 1
        expected_logging_start1 = datetime(2017, 1, 1, 1, 1, 1)
        sample_times = [datetime(2001, 2, 3, 4, 5, 6), datetime(2001, 2, 3, 4, 5, 36), datetime(2001, 2, 3, 4, 6, 6)]
        data_changes = [[],
                        [(datetime(2017, 1, 1, 1, 1, 2), 0, 0),
                        (datetime(2017, 1, 1, 1, 2, 2), 0, 1),
                        (datetime(2017, 1, 1, 1, 3, 2), 0, 0)]]
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], data_changes=data_changes, sample_times=sample_times, logging_start_times=[expected_logging_start1])
        expected_period = timedelta(seconds=log_period_in_second)
        expected_logging_stop_time1 = datetime(2017, 1, 1, 1, 1, 2)
        expected_logging_start_time2 = datetime(2017, 1, 1, 1, 2, 2)
        expected_logging_stop_time2 = datetime(2017, 1, 1, 1, 3, 2)

        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second])

        log_file_initiator.check_initiated()
        log_file_initiator.check_initiated()

        arg_list = self.log_file_creators[0].write_complete_file.call_args_list
        logging_time_period1 = arg_list[0][0][0]

        assert_that(logging_time_period1.delta, is_(expected_period))
        assert_that(logging_time_period1.start_time, is_(expected_logging_start1))
        assert_that(logging_time_period1.end_time, is_(expected_logging_stop_time1))

        logging_time_period2 = arg_list[1][0][0]
        assert_that(logging_time_period2.delta, is_(expected_period))
        assert_that(logging_time_period2.start_time, is_(expected_logging_start_time2))
        assert_that(logging_time_period2.end_time, is_(expected_logging_stop_time2))

    def test_GIVEN_multiple_configs_with_pv_WHEN_pvs_has_changed_from_1_to_0_THEN_multiple_log_files_created(self):
        log_period_in_second1 = 1
        log_period_in_second2 = 0.1
        expected_period_config_1 = timedelta(seconds=log_period_in_second1)
        expected_period_config_2 = timedelta(seconds=log_period_in_second2)
        expected_logging_start_config_1 = datetime(2017, 1, 1, 1, 1, 1)
        expected_logging_start_config_2 = datetime(2017, 1, 1, 3, 4, 5)
        logging_stop_time_config_1 = datetime(2017, 1, 1, 1, 1, 2)
        logging_stop_time_config_2 = datetime(2017, 1, 1, 1, 2, 2)

        data_changes = [[(datetime(2017, 1, 1, 1, 1, 2), 0, 0),
                         (datetime(2017, 1, 1, 1, 2, 2), 1, 0)]]

        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1, 1], data_changes=data_changes, logging_start_times=[expected_logging_start_config_1, expected_logging_start_config_2] )
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second1, log_period_in_second2])

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_called_once()
        logging_time_period = self.log_file_creators[0].write_complete_file.call_args[0][0]
        assert_that(logging_time_period.delta, is_(expected_period_config_1))
        assert_that(logging_time_period.start_time, is_(expected_logging_start_config_1))
        assert_that(logging_time_period.end_time, is_(logging_stop_time_config_1))

        self.log_file_creators[2].write_complete_file.assert_called_once()
        logging_time_period = self.log_file_creators[2].write_complete_file.call_args[0][0]
        assert_that(logging_time_period.delta, is_(expected_period_config_2))
        assert_that(logging_time_period.start_time, is_(expected_logging_start_config_2))
        assert_that(logging_time_period.end_time, is_(logging_stop_time_config_2))

    def test_GIVEN_config_with_logging_period_which_is_a_pv_WHEN_log_THEN_logging_period_is_pv_value(self):
        log_period_in_second = 2.0
        expected_period = timedelta(seconds=log_period_in_second)
        pv_name = "myperiodpv"
        logging_period_pv_values = {pv_name + ".VAL": log_period_in_second}
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], final_pv_value=0, logging_period_pv_values=logging_period_pv_values)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_pvs=[pv_name])

        log_file_initiator.check_initiated()

        self.log_file_creators[0].write_complete_file.assert_called_once()
        logging_time_period = self.log_file_creators[0].write_complete_file.call_args[0][0]
        assert_that(logging_time_period.delta, is_(expected_period))

    def test_GIVEN_config_with_pv_WHEN_pv_has_changed_from_1_to_0_and_write_file_throws_THEN_no_error_thrown_log_not_written(self):
        log_period_in_second = 1
        archive_data_source = DataSourceMother.set_up_data_source(initial_pv_values=[1], final_pv_value=0)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, log_period_in_seconds=[log_period_in_second], throw_on_write_complete_file=True)

        try:
            log_file_initiator.check_initiated()
        except Exception as e:
            self.fail("If underlying call throws then this should catch and logs. Error: '{}'".format(e))

        self.log_file_creators[0].write_complete_file.assert_called_once()


    def test_GIVEN_config_with_pv_WHEN_get_data__and_no_new_sample_time_THEN_sample_time_is_current_time_minus_set_amount(self):
        last_sample_time = datetime(2001, 2, 3, 4, 5, 6)
        current_time = datetime(2001, 2, 3, 4, 7, 0)
        expected_to_sample_time = current_time - SAMPLING_BEHIND_REAL_TIME
        sample_times = [last_sample_time, last_sample_time]
        archive_data_source = DataSourceMother.set_up_data_source(sample_times=sample_times)
        log_file_initiator, self.log_file_creators = DataSourceMother.create_log_file_intiator(archive_data_source, current_time=current_time)

        log_file_initiator.check_initiated()

        assert_that(archive_data_source.to_sample_time, is_([expected_to_sample_time]))

class DataSourceMother(object):
    @staticmethod
    def set_up_data_source(initial_pv_values=None,
                            final_pv_value=0,
                            logging_start_times=None,
                            logging_stop_time=datetime(2017, 1, 1, 1, 1, 2),
                            sample_times=None,
                            data_changes=None,
                            logging_period_pv_values=None,
                            sample_ids=None):

        if initial_pv_values is None:
            initial_pv_values = [1]
        if logging_start_times is None:
            logging_start_times = [datetime(2017, 1, 1, 1, 1, 1)] * len(initial_pv_values)
        initial_archiver_data_values = []
        for initial_pv_value, logging_start_time in zip(initial_pv_values, logging_start_times):
            initial_archiver_data_value = ArchiverDataValue()
            initial_archiver_data_value.num_val = initial_pv_value
            initial_archiver_data_value.sample_time = logging_start_time
            initial_archiver_data_values.append(initial_archiver_data_value)

        if data_changes is None:
            data_changes = [[(logging_stop_time, 0, final_pv_value)]]
        if sample_times is None:
            sample_times = [datetime(2010, 9, 8, 2, 3, 4), datetime(2010, 9, 8, 2, 3, 34)]
        if sample_ids is None:
            sample_ids = [datetime(2010, 9, 8, 2, 3, 4), datetime(2010, 9, 8, 2, 3, 34)]

        archive_data_source = ArchiverDataStub(initial_archiver_data_value=initial_archiver_data_values,
                                               data_changes=data_changes,
                                               sample_times=sample_times,
                                               initial_values=logging_period_pv_values,
                                               sample_ids=sample_ids)
        return archive_data_source

    @staticmethod
    def create_log_file_intiator(archive_data_source, log_period_in_seconds=None, log_period_pvs=None, throw_on_write_complete_file=False,
                                 write_file_header_mock=Mock(), write_data_lines_mock=Mock(), finish_log_file_mock=Mock(),
                                 current_time=datetime(2000, 1, 1, 1, 1, 2), time_last_actived=datetime(2000, 1, 1, 1, 1, 1),
                                 sample_id_last_active=123):
        if log_period_in_seconds is None and log_period_pvs is None:
            log_period_in_seconds = [1]
        if log_period_pvs is None:
            log_period_pvs = [None] * len(log_period_in_seconds)
        if log_period_in_seconds is None:
            log_period_in_seconds = [None] * len(log_period_pvs)

        configs = []
        log_file_creators = []
        for log_period_in_second, log_period_pv in zip(log_period_in_seconds, log_period_pvs):
            log_file_creator = Mock()
            if throw_on_write_complete_file:
                log_file_creator.write_complete_file = Mock(side_effect=DataFileCreationError("Test problem"))
            else:
                log_file_creator.write_complete_file = Mock()
            log_file_creator.write_file_header = write_file_header_mock
            log_file_creator.write_data_lines = write_data_lines_mock
            log_file_creator.finish_log_file = finish_log_file_mock
            config_builder = ArchiveAccessConfigBuilder("log_file{start_time}").trigger_pv("my_pv")
            if log_period_in_second is not None:
                config = config_builder.logging_period_seconds(log_period_in_second).build()
            else:
                config = config_builder.logging_period_pv(log_period_pv).build()
            configs.append(config)
            log_file_creators.append(log_file_creator)  # one for continuous logging
            log_file_creators.append(log_file_creator)  # one for one end logging
        time_last_active = Mock()
        sample_id = sample_id_last_active
        time_last_active.get = Mock(return_value=(time_last_actived, sample_id))

        def get_current_time():
            return current_time

        data_file_creator_factory = Mock()
        data_file_creator_factory.create = Mock(side_effect=log_file_creators)

        return LogFileInitiatorOnPVChange(configs, archive_data_source, time_last_active, get_current_time, data_file_creator_factory), log_file_creators
