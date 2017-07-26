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
from ArchiverAccess.utilities import add_default_field


class TestUtilities(TestCase):

    def test_GIVEN_pv_no_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = ""
        pv = "pv:name"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_default_is_none_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = None
        pv = "pv:name"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_is_none_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = None
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_is_blank_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = ""
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_has_field_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = "pv.field"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_no_field_and_default_WHEN_pv_with_default_THEN_pv_has_field_with_dot(self):
        default_field = "VAL"
        pv = "pv"
        expected_pv = pv + "." + default_field

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))
