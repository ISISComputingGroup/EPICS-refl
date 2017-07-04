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
from ArchiverAccess.configuration import ConfigBuilder, TIME_DATE_COLUMN_HEADING
from ArchiverAccess.test_modules.stubs import ArchiverDataStub, FileStub


class TestlogFileCreator(TestCase):

    def _archive_data_file_creator_setup(self,
                                         config,
                                         time_period=ArchiveTimePeriod(datetime(2017, 1, 1, 1, 2, 3, 0), timedelta(seconds=10), 10),
                                         initial_values=None,
                                         values= None):
        if values is None:
            values = {}
        if initial_values is None:
            initial_values = {}
        archiver_data_source = ArchiverDataStub(initial_values, values)
        return ArchiveDataFileCreator(config, time_period, archiver_data_source, FileStub)

    def test_GIVEN_config_is_just_constant_header_line_WHEN_write_THEN_values_are_written_to_file(self):
        expected_header_line = "expected_header_line a line of goodness :-)"
        config = ConfigBuilder("filename.txt").header(expected_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config)

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header_line))

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
        file_creator = self._archive_data_file_creator_setup(config, initial_values={pvname: expected_pv_value})

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header_line))

    def test_GIVEN_config_is_line_with_realistic_pv_in_WHEN_write_THEN_pv_is_replaced_with_value_at_time(self):
        expected_pv_value = 12.9
        pvname = "IN:INST:IOC_01:01:VALUE"
        template_header_line = "expected_header_line a line {{{0}}}".format(pvname)
        expected_header_line = "expected_header_line a line 12.9"

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values={pvname: expected_pv_value})

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header_line))

    def test_GIVEN_multiple_line_in_header_with_pvs_in_WHEN_write_THEN_pvs_are_replaced_with_value_at_time(self):
        values = {'pvname1': 12, 'pvname2':"hi"}
        template_header_line1 = "expected_header_line a line {pvname1}"
        expected_header_line1 = template_header_line1.format(pvname1=12)
        template_header_line2 = "expected_header_line a line {pvname1} and {pvname2}"
        expected_header_line2 = template_header_line2.format(pvname1=12, pvname2="hi")

        config = ConfigBuilder("filename.txt").header(template_header_line1).header(template_header_line2).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=values)

        file_creator.write()

        assert_that(FileStub.file_contents[0:2], is_([expected_header_line1, expected_header_line2]))

    def test_GIVEN_config_is_header_with_pv_with_formatting_WHEN_write_THEN_pv_is_replaced_with_value_at_time(self):
        expected_pv_value = 12.9
        pvname = "pvname"
        template_header_line = "expected_header_line a line {{{0}|.3f}}".format(pvname)
        expected_header_line = "expected_header_line a line 12.900"

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values={pvname: expected_pv_value})

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header_line))

    def test_GIVEN_config_is_header_with_pv_with_formatting_error_WHEN_write_THEN_pv_is_replaced_with_value_no_formatting(self):
        expected_pv_value = "disconnected"
        pvname = "pvname"
        template_header_line = "expected_header_line a line {{{0}|.3f}}".format(pvname)
        expected_header_line = "expected_header_line a line disconnected{0}"\
            .format(FORMATTER_NOT_APPLIED_MESSAGE
                   .format("Unknown format code 'f' for object of type 'str'"))

        config = ConfigBuilder("filename.txt").header(template_header_line).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values={pvname: expected_pv_value})

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header_line))

    def test_GIVEN_config_has_column_heading_WHEN_write_THEN_table_has_correct_heading(self):
        heading = "PV Heading"
        expected_header = TIME_DATE_COLUMN_HEADING + "\t" + heading
        pvname = "pvname"

        config = ConfigBuilder("filename.txt").table_column(heading, pvname).build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=[1.0])

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_(expected_header))

    def test_GIVEN_config_has_many_column_headings_WHEN_write_THEN_table_has_correct_headings(self):
        expected_heading1 = "PV Heading"
        expected_heading2 = "PV Heading2"
        expected_heading3 = "PV Heading3"

        config = ConfigBuilder("filename.txt")\
            .table_column(expected_heading1, "pvname") \
            .table_column(expected_heading2, "pvname2") \
            .table_column(expected_heading3, "pvnam3")\
            .build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=[1.0, 2.0, 3.0])

        file_creator.write()

        assert_that(FileStub.file_contents[0], is_("\t".join([TIME_DATE_COLUMN_HEADING, expected_heading1, expected_heading2, expected_heading3])))

    def test_GIVEN_config_with_1_column_and_initial_data_WHEN_write_THEN_table_has_initial_data(self):
        time_period = ArchiveTimePeriod(datetime(2017, 1, 1, 1, 2, 3, 0), timedelta(seconds=10), 10)
        pvname = "pvname"
        initial_value = 2.91
        expected_line = "2017-01-01T01:02:03\t{0}".format(initial_value)
        config = ConfigBuilder("filename.txt")\
            .table_column("heading", "{%s}" % pvname)\
            .build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values={pvname: initial_value}, time_period=time_period)

        file_creator.write()

        assert_that(FileStub.file_contents[1], is_(expected_line))

    def test_GIVEN_config_with_3_column_and_initial_data_WHEN_write_THEN_table_has_initial_data(self):
        time_period = ArchiveTimePeriod(datetime(2017, 1, 1, 1, 2, 3, 0), timedelta(seconds=10), 10)
        initial_values = {"pvname1": 2.91, "pvname2": "hi", "pvname3": 5, "time": ""}
        expected_line = "{0}\t{pvname1}\t{pvname2}\t{pvname3}".format("2017-01-01T01:02:03", **initial_values)
        config = ConfigBuilder("filename.txt") \
            .table_column("heading1", "{%s}" % "pvname1") \
            .table_column("heading2", "{%s}" % "pvname2")  \
            .table_column("heading3", "{%s}" % "pvname3") \
            .build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=initial_values, time_period=time_period)

        file_creator.write()

        assert_that(FileStub.file_contents[1], is_(expected_line))


    def test_GIVEN_config_with_3_column_and_full_data_with_header_WHEN_write_THEN_contents_is_full_log_file(self):
        expected_start_time = datetime(2017, 1, 1, 1, 2, 3, 0)
        time_period = ArchiveTimePeriod(expected_start_time, timedelta(seconds=10), 10)

        rn0 = 123456
        rn1 = 123457
        pos0 = 12.3
        pos1 = 23.1245
        pos2 = 34678
        load0 = 2452.24432343
        load1 = 23
        strain0 = 7.98
        strain1 = 183
        initial_values = {"IN:PV:CSA": 2.91, "IN:PV:GLS": 123.8764, "IN:PV:RBNum": 123456789,
                          "RunNumber": rn0, "POS": pos0, "Load": load0, "Strain": strain0}
        values = [
            [expected_start_time + timedelta(seconds=35), "RunNumber", rn1],
            [expected_start_time + timedelta(seconds=36), "POS",  pos1],
            [expected_start_time + timedelta(seconds=41), "POS", pos2],
            [expected_start_time + timedelta(seconds=61), "Load", load1],
            [expected_start_time + timedelta(seconds=70), "Strain", strain1]
        ]

        table_format = "{0}\t{1:6d}\t{2:10.6f}\t{3:10.6f}\t{4:10.6f}"
        expected_file_contents = [
            "Cross Sectional Area = 2.910000",
            "Gauge Length for strain = 123.876400",
            "RB Number = 123456789",
            "",
            "\t".join((TIME_DATE_COLUMN_HEADING, "Run Number",  "Position", "Load", "Strain")),
            table_format.format("2017-01-01T01:02:03", rn0, pos0, load0, strain0),
            table_format.format("2017-01-01T01:02:13", rn0, pos0, load0, strain0),
            table_format.format("2017-01-01T01:02:23", rn0, pos0, load0, strain0),
            table_format.format("2017-01-01T01:02:33", rn0, pos0, load0, strain0),
            table_format.format("2017-01-01T01:02:43", rn1, pos1, load0, strain0),
            table_format.format("2017-01-01T01:02:53", rn1, pos2, load0, strain0),
            table_format.format("2017-01-01T01:03:03", rn1, pos2, load0, strain0),
            table_format.format("2017-01-01T01:03:13", rn1, pos2, load1, strain1),
            table_format.format("2017-01-01T01:03:23", rn1, pos2, load1, strain1),
            table_format.format("2017-01-01T01:03:33", rn1, pos2, load1, strain1)
        ]

        config = ConfigBuilder("filename.txt") \
            .header("Cross Sectional Area = {IN:PV:CSA|.6f}") \
            .header("Gauge Length for strain = {IN:PV:GLS|.6f}") \
            .header("RB Number = {IN:PV:RBNum|9d}") \
            .header("") \
            .table_column("Run Number", "{%s|6d}" % "RunNumber") \
            .table_column("Position", "{%s|10.6f}" % "POS")  \
            .table_column("Load", "{%s|10.6f}" % "Load") \
            .table_column("Strain", "{%s|10.6f}" % "Strain") \
            .build()
        file_creator = self._archive_data_file_creator_setup(config, initial_values=initial_values, time_period=time_period, values=values)

        file_creator.write()

        for index, (actual, expected) in enumerate(zip(FileStub.file_contents, expected_file_contents)):
            assert_that(actual, is_(expected), "Error on line {0}".format(index))
