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

from ArchiverAccess.test_modules.stubs import FileStub
from ArchiverAccess.time_last_active import TimeLastActive, TIME_LAST_ACTIVE_HEADER, TIME_LAST_ACTIVE_FILENAME, \
    DEFAULT_DELTA


class TestTimeLastActive(TestCase):

    def test_GIVEN_there_is_time_last_active_file_WHEN_get_time_last_active_THEN_date_time_in_file_returned(self):
        expected_time = datetime(2016, 1, 2, 3, 4, 5)
        time_last_active = self._setup_last_active_time(expected_time, 1, expected_time + timedelta(seconds=10))

        result, _ = time_last_active.get()

        assert_that(result, is_(expected_time))

    def test_GIVEN_there_is_time_last_active_file_WHEN_get_time_last_active_THEN_last_sample_in_file_returned(self):
        expected_sample_id = 123
        time = datetime(2016, 1, 2, 3, 4, 5)
        time_last_active = self._setup_last_active_time(time, 1, time + timedelta(seconds=10), expected_sample_id)

        _, result = time_last_active.get()

        assert_that(result, is_(expected_sample_id))

    def test_GIVEN_there_is_time_last_active_file_which_is_earlier_than_max_allowed_WHEN_get_time_last_active_THEN_current_date_minus_max_is_returned_sample_id_is_still_id_in_file(self):
        max_delta = 2
        time_now = datetime(2016, 1, 6, 3, 4, 5)
        expected_time = datetime(2016, 1, 4, 3, 4, 5)
        early_time = datetime(2015, 1, 2, 3, 4, 5)
        expected_sample_id = 123
        time_last_active = self._setup_last_active_time(early_time, max_delta, time_now, expected_sample_id)

        result, resule_sample_id = time_last_active.get()

        assert_that(result, is_(expected_time))
        assert_that(resule_sample_id,  is_(expected_sample_id))

    def test_GIVEN_delta_is_negative_WHEN_get_time_last_active_THEN_current_date_minus_1(self):
        max_delta = -2
        time_now = datetime(2016, 1, 6, 3, 4, 5)
        expected_time = datetime(2016, 1, 5, 3, 4, 5)
        early_time = datetime(2015, 1, 2, 3, 4, 5)
        time_last_active = self._setup_last_active_time(early_time, max_delta, time_now)

        result, _ = time_last_active.get()

        assert_that(result, is_(expected_time))

    def test_GIVEN_delta_is_not_a_number_WHEN_get_time_last_active_THEN_current_date_minus_default(self):
        max_delta = "hi"
        time_now = datetime(2016, 1, 6, 3, 4, 5)
        expected_time = datetime(2016, 1, 5, 3, 4, 5)
        early_time = datetime(2015, 1, 2, 3, 4, 5)
        time_last_active = self._setup_last_active_time(early_time, max_delta, time_now)

        result, _ = time_last_active.get()

        assert_that(result, is_(expected_time))

    def test_GIVEN_last_time_is_invalid_WHEN_get_time_last_active_THEN_current_time_minus_default_delta(self):
        max_delta = 2
        time_now = datetime(2016, 1, 6, 3, 4, 5)
        expected_time = datetime(2016, 1, 5, 3, 4, 5)
        last_active_time = "blah"
        time_last_active = self._setup_last_active_time(last_active_time, max_delta, time_now)

        result, _ = time_last_active.get()

        assert_that(result, is_(expected_time))

    def test_GIVEN_last_time_active_WHEN_set_time_last_active_THEN_file_contains_last_time_active(self):
        last_active_time = datetime(2016, 1, 5, 3, 4, 5)
        time_last_active = TimeLastActive(file_cls=FileStub)
        sample_id = 213

        time_last_active.set(last_active_time, sample_id)

        assert_that(FileStub.contents_of_only_file(), is_([TIME_LAST_ACTIVE_HEADER, last_active_time.isoformat(), str(DEFAULT_DELTA), str(sample_id)]))

    def _setup_last_active_time(self, last_active_time, max_delta_in_days, time_now, sample_id=100):

        def time_now_fn():
            return time_now

        FileStub.clear()
        try:
            FileStub.add_file([TIME_LAST_ACTIVE_HEADER, last_active_time.isoformat(), max_delta_in_days, sample_id], TIME_LAST_ACTIVE_FILENAME)
        except AttributeError:
            FileStub.add_file([TIME_LAST_ACTIVE_HEADER, last_active_time, max_delta_in_days, sample_id], TIME_LAST_ACTIVE_FILENAME)

        file_stub = FileStub
        time_last_active = TimeLastActive(file_cls=file_stub, time_now_fn=time_now_fn)
        return time_last_active
