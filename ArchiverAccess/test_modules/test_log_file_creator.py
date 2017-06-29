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


class TestlogFileCreator(TestCase):

    def _archive_data_file_creator_setup(self,
                                         config,
                                         time_period=ArchiveTimePeriod(datetime(2017, 1, 1, 1, 2, 3, 0), timedelta(seconds=10), 10),
                                         initial_values = [],
                                         values= []):
        archiver_data_source = ArchiverDataStub(initial_values, values)
        return ArchiveDataFileCreator(config, time_period, archiver_data_source, FileStub)

    def test_GIVEN_config_is_just_constant_header_line_WHEN_write_THEN_values_are_written_to_file(self):
        expected_header_line = "expected_header_line a line of goodness :-)"
        config = ConfigBuilder("filename.txt").header(expected_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config)

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line]))

    def test_GIVEN_config_contains_plain_filename_WHEN_write_THEN_file_is_opened(self):
        expected_filename = "filename.txt"
        config = ConfigBuilder(expected_filename).build()
        file_creator = self._archive_data_file_creator_setup(config)

        file_creator.write()

        assert_that(FileStub.filename, is_(expected_filename))

    def test_GIVEN_config_contains_templated_filename_WHEN_write_THEN_filename_is_correct(self):
        filename_template = "c:\log\:filename{start_time}.txt"
        expected_filename = filename_template.format(start_time="2017-06-10T12:11:10")
        time_period = ArchiveTimePeriod(datetime(2017, 06, 10, 12, 11, 10, 7), timedelta(seconds=10), 10)

        config = ConfigBuilder(filename_template).build()
        file_creator = self._archive_data_file_creator_setup(config, time_period)

        file_creator.write()

        assert_that(FileStub.filename, is_(expected_filename))

    def test_GIVEN_config_is_line_with_pv_in_WHEN_write_THEN_pv_is_replaced_with_value_at_time(self):
        expected_pv_value = 12.9
        pvname = "pvname"
        template_header_line = "expected_header_line a line {{{0}}}".format(pvname)
        expected_header_line = template_header_line.format(pvname=expected_pv_value)

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=[expected_pv_value])

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line]))

    def test_GIVEN_multiple_line_in_header_with_pvs_in_WHEN_write_THEN_pvs_are_replaced_with_value_at_time(self):
        values = {"pvname1": 12, "pvname2":"hi"}
        template_header_line1 = "expected_header_line a line {pvname1}"
        expected_header_line1 = template_header_line1.format(pvname1=12)
        template_header_line2 = "expected_header_line a line {pvname1} and {pvname2}"
        expected_header_line2 = template_header_line2.format(pvname1=12, pvname2="hi")

        config = ConfigBuilder("filename.txt").header(template_header_line1).header(template_header_line2).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=values.values())

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line1, expected_header_line2]))

    def test_GIVEN_config_is_header_with_pv_with_formatting_WHEN_write_THEN_pv_is_replaced_with_value_at_time(self):
        expected_pv_value = 12.9
        pvname = "pvname"
        template_header_line = "expected_header_line a line {{{0}:.3f}}".format(pvname)
        expected_header_line = "expected_header_line a line 12.900"

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=[expected_pv_value])

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line]))

    def test_GIVEN_config_is_header_with_pv_with_formatting_error_WHEN_write_THEN_pv_is_replaced_with_value_no_formatting(self):
        expected_pv_value = "disconnected"
        pvname = "pvname"
        template_header_line = "expected_header_line a line {{{0}:.3f}}".format(pvname)
        expected_header_line = "expected_header_line a line disconnected{0}".format(FORMATTER_NOT_APPLIED_MESSAGE)

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=[expected_pv_value])

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line]))
