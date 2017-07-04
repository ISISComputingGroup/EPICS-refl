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
from mock import Mock

from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator, FORMATTER_NOT_APPLIED_MESSAGE
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.configuration import ConfigBuilder
from ArchiverAccess.test_modules.stubs import ArchiverDataStub, FileStub


class TestConfiguration(TestCase):

    def test_GIVEN_config_has_plain_header_WHEN_get_header_THEN_plain_header_returned(self):
        expected_header_line = "expected_header_line a line of goodness :-)"
        config = ConfigBuilder("filename.txt").header(expected_header_line).build()

        results = config.header

        assert_that(results, is_([expected_header_line]))

    def test_GIVEN_config_has_2_plain_header_WHEN_get_header_THEN_plain_headers_returned(self):
        expected_header_line1 = "expected_header_line a line of goodness :-)"
        expected_header_line2 = "line 2"
        config = ConfigBuilder("filename.txt")\
            .header(expected_header_line1) \
            .header(expected_header_line2)\
            .build()

        results = config.header

        assert_that(results, contains(expected_header_line1, expected_header_line2))

    def test_GIVEN_config_has_header_with_template_WHEN_get_header_THEN_header_with_template_returned_with_pv(self):
        pvname= "pv_name"
        header_line = "{pv_name|5.6f}"
        expected_header_line = "{0:5.6f}"
        config = ConfigBuilder("filename.txt").header(header_line).build()

        results = config.header

        assert_that(results, contains(expected_header_line))
        assert_that(config.pv_names_in_header, contains(pvname))

    def test_GIVEN_config_has_header_with_template_no_formatter_WHEN_get_header_THEN_header_with_template_returned_with_pv(self):
        pvname= "pv_name"
        header_line = "{pv_name}"
        expected_header_line = "{0}"
        config = ConfigBuilder("filename.txt").header(header_line).build()

        results = config.header

        assert_that(results, contains(expected_header_line))
        assert_that(config.pv_names_in_header, contains(pvname))

    def test_GIVEN_config_has_header_with_converter_template_WHEN_get_header_THEN_header_with_template_returned_with_pv(self):
        pvname= "pv_name"
        header_line = "{pv_name!s|5.6f}"
        expected_header_line = "{0!s:5.6f}"
        config = ConfigBuilder("filename.txt").header(header_line).build()

        results = config.header

        assert_that(results, contains(expected_header_line))
        assert_that(config.pv_names_in_header, contains(pvname))

    def test_GIVEN_config_has_header_with_converter_template_no_formatter_WHEN_get_header_THEN_header_with_template_returned_with_pv(self):
        pvname= "pv_name"
        header_line = "{pv_name!s}"
        expected_header_line = "{0!s}"
        config = ConfigBuilder("filename.txt").header(header_line).build()

        results = config.header

        assert_that(results, contains(expected_header_line))
        assert_that(config.pv_names_in_header, contains(pvname))

    def test_GIVEN_config_has_header_with_multiple_repeating_pvs_WHEN_get_header_THEN_header_with_template_returned_with_pv(self):
        pvname1= "pv_name1"
        pvname2 = "pv_name2"
        pvname3 = "pv_name3"
        header_line1 = "{pv_name1|5.6f} but plain is {pv_name1}, {pv_name2}"
        expected_header_line1 = "{0:5.6f} but plain is {0}, {1}"
        header_line2 = "{pv_name2} pv_name2 pv_name1 {pv_name3}"
        expected_header_line2 = "{1} pv_name2 pv_name1 {2}"

        config = ConfigBuilder("filename.txt").header(header_line1).header(header_line2).build()

        results = config.header

        assert_that(results, contains(expected_header_line1, expected_header_line2))
        assert_that(config.pv_names_in_header, contains(pvname1, pvname2, pvname3))
