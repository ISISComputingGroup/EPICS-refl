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

from ArchiverAccess.archiver_data_source import ArchiverDataValue
from ArchiverAccess.configuration import ConfigBuilder
from ArchiverAccess.log_file_initiator import LogFileInitiatorOnPVChange, ConfigAndDependencies
from ArchiverAccess.logging_period_providers import LoggingPeriodProviderConst, LoggingPeriodProviderPV, \
    MINIMUM_LOGGING_PERIOD
from ArchiverAccess.test_modules.stubs import ArchiverDataStub
from server_common.mysql_abstraction_layer import DatabaseError


class TestLogPeriodProvider(unittest.TestCase):

    def test_GIVEN_constant_value_WHEN_get_value_THEN_value_is_value_as_time_detla_in_second(self):
        log_period = 1
        expected_log_period = timedelta(seconds=log_period)
        log_provider = LoggingPeriodProviderConst(log_period)

        result = log_provider.get_logging_period(None, None)

        assert_that(result, is_(expected_log_period))

    def test_GIVEN_pv_value_with_val_WHEN_get_value_THEN_value_is_val_as_time_delta(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={pv_name: log_period})
        log_provider = LoggingPeriodProviderPV(pv_name, 100)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))

    def test_GIVEN_pv_value_with_error_WHEN_get_value_THEN_value_is_default(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub()
        archive_data_source.initial_values = Mock(side_effect=DatabaseError("test"))
        log_provider = LoggingPeriodProviderPV(pv_name, log_period)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))


    def test_GIVEN_pv_value_with_disconnect_WHEN_get_value_THEN_value_is_default_on_error(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={pv_name: "disconnected"})
        log_provider = LoggingPeriodProviderPV(pv_name, log_period)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))

    def test_GIVEN_pv_value_is_negative_WHEN_get_value_THEN_value_is_default_on_error(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={pv_name: -1})
        log_provider = LoggingPeriodProviderPV(pv_name, log_period)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))

    def test_GIVEN_pv_value_is_zero_WHEN_get_value_THEN_value_is_default_on_error(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={pv_name: 0})
        log_provider = LoggingPeriodProviderPV(pv_name, log_period)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))

    def test_GIVEN_pv_value_is_too_small_WHEN_get_value_THEN_value_is_default_on_error(self):
        log_period = 1
        pv_name = "pvname"
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={pv_name: MINIMUM_LOGGING_PERIOD*0.9})
        log_provider = LoggingPeriodProviderPV(pv_name, log_period)

        result = log_provider.get_logging_period(archive_data_source, None)

        assert_that(result, is_(expected_log_period))
