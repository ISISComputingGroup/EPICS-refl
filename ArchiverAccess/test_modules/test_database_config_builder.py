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
import os
from unittest import TestCase

from datetime import timedelta
from hamcrest import *
from mock import Mock

from ArchiverAccess.archive_access_configuration import DEFAULT_LOGGING_PERIOD_IN_S, DEFAULT_LOG_PATH
from ArchiverAccess.archive_access_config_builder import ArchiverAccessDatabaseConfigBuilder
from ArchiverAccess.test_modules.stubs import ArchiverDataStub


class TestDatabaseConfigBuilder(TestCase):

    def test_GIVEN_ioc_name_WHEN_generate_THEN_configuration_with_correct_file_name_template_is_created(self):
        ioc_name = "myioc"
        expected_filename_template = os.path.join(DEFAULT_LOG_PATH, "myioc", "myioc_{start_time}.dat")
        expected_continous_filename_template = os.path.join(DEFAULT_LOG_PATH, "myioc",
                                                            "myioc_{start_time}_continuous.dat")
        ioc_data_source = self._create_ioc_data_source(ioc_name=ioc_name)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].on_end_logging_filename_template, is_(expected_filename_template))
        assert_that(config[0].continuous_logging_filename_template, is_(expected_continous_filename_template))

    def test_GIVEN_header_line_in_database_WHEN_generate_THEN_configuration_is_created(self):
        expected_header_line = "expected_header_line a line of goodness :-)"
        ioc_data_source = self._create_ioc_data_source(header_lines=[expected_header_line])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].header, is_([expected_header_line]))

    def test_GIVEN_templated_header_line_in_database_WHEN_generate_THEN_configuration_is_created(self):
        pv_name = "pv:name"
        expected_pv_name = pv_name + ".VAL"
        header_line = "Header line with pv {this_pv}"
        expected_header_line = header_line.format(this_pv="{0}")
        ioc_data_source = self._create_ioc_data_source(header_lines=[header_line], header_pvs=[pv_name])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].header, is_([expected_header_line]))
        assert_that(config[0].pv_names_in_header, is_([expected_pv_name]))

    def test_GIVEN_multiple_header_line_in_database_WHEN_generate_THEN_configuration_is_created(self):
        expected_header_lines = ["line 1", "line2", "line3"]
        ioc_data_source = self._create_ioc_data_source(header_lines=expected_header_lines)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].header, is_(expected_header_lines))

    def test_GIVEN_multiple_header_line_in_funny_order_with_repeated_indexes_and_different_cases_WHEN_generate_THEN_configuration_is_created(self):
        expected_header_lines = ["line 1", "line2", "line3", "line4"]
        header_lines_section = [("pvname", "LoG_header6", expected_header_lines[3]),
                                ("pvname", "LOG_header4", expected_header_lines[1]),
                                ("pvname", "LOG_Header1", expected_header_lines[0]),
                                ("pvname", "LOG_header4", expected_header_lines[2])]

        ioc_data_source = self._create_ioc_data_source(header_lines_section=header_lines_section)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].header, is_(expected_header_lines))

    def test_GIVEN_trigger_pv_only_marked_WHEN_generate_THEN_configuration_has_trigger_pv_in(self):
        expected_trigger_pv = "inst:triggerpv.val"
        ioc_data_source = self._create_ioc_data_source(trigger_pv=expected_trigger_pv, trigger_pv_template="")
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].trigger_pv, is_(expected_trigger_pv))

    def test_GIVEN_trigger_pv_is_templated_WHEN_generate_THEN_configuration_has_trigger_pv_in(self):
        expected_trigger_pv = "inst:triggerpv.val"
        ioc_data_source = self._create_ioc_data_source(trigger_pv=expected_trigger_pv)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].trigger_pv, is_(expected_trigger_pv))

    def test_GIVEN_trigger_pv_is_explicit_WHEN_generate_THEN_configuration_has_trigger_pv_in(self):
        trigger_pv = "diff:triggerpv"
        expected_trigger_pv = trigger_pv + ".VAL"
        ioc_data_source = self._create_ioc_data_source(trigger_pv="blah", trigger_pv_template=trigger_pv)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].trigger_pv, is_(expected_trigger_pv))

    def test_GIVEN_logging_period_pv_is_only_marked_WHEN_generate_THEN_configuration_has_logging_period_pv(self):
        period_pv = "diff:triggerpv.VAL"
        ioc_data_source = self._create_ioc_data_source(period_pv=period_pv, period_pv_template="")
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)
        log_period = 10
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={period_pv: log_period})

        config = db_config_builder.create()

        logging_period = config[0].logging_period_provider.get_logging_period(archive_data_source, None)
        assert_that(logging_period, is_(expected_log_period))

    def test_GIVEN_logging_period_pv_is_templated_WHEN_generate_THEN_configuration_has_logging_period_pv(self):
        period_pv = "diff:triggerpv"
        ioc_data_source = self._create_ioc_data_source(period_pv=period_pv, period_pv_template="this_pv")
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)
        log_period = 10
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={period_pv + ".VAL": log_period})

        config = db_config_builder.create()

        logging_period = config[0].logging_period_provider.get_logging_period(archive_data_source, None)
        assert_that(logging_period, is_(expected_log_period))

    def test_GIVEN_logging_period_pv_is_explicit_WHEN_generate_THEN_configuration_has_logging_period_pv(self):
        period_pv = "diff:triggerpv.field"
        ioc_data_source = self._create_ioc_data_source(period_pv="blah", period_pv_template=period_pv)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)
        log_period = 10
        expected_log_period = timedelta(seconds=log_period)
        archive_data_source = ArchiverDataStub(initial_values={period_pv: log_period})

        config = db_config_builder.create()

        logging_period = config[0].logging_period_provider.get_logging_period(archive_data_source, None)
        assert_that(logging_period, is_(expected_log_period))

    def test_GIVEN_logging_period_is_a_constant_WHEN_generate_THEN_configuration_has_correct_logging_period(self):
        expected_log_period = 10
        ioc_data_source = self._create_ioc_data_source(period_constant=expected_log_period)
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        logging_period = config[0].logging_period_provider.get_logging_period(None, None)
        assert_that(logging_period, is_(timedelta(seconds=expected_log_period)))

    def test_GIVEN_logging_period_is_a_constant_which_is_invalid_WHEN_generate_THEN_configuration_has_default_logging_period(self):
        ioc_data_source = self._create_ioc_data_source(period_constant="invalid")
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        logging_period = config[0].logging_period_provider.get_logging_period(None, None)
        assert_that(logging_period, is_(timedelta(seconds=DEFAULT_LOGGING_PERIOD_IN_S)))

    def test_GIVEN_column_with_only_header_in_database_WHEN_generate_THEN_configuration_has_assoicated_pv_and_header(self):
        expected_column_header = "column header"
        pv_name = "pv:name"
        expected_pv_name = pv_name + ".VAL"
        ioc_data_source = self._create_ioc_data_source(column_headers=[(pv_name, 1, expected_column_header)])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].column_header_list[1], is_(expected_column_header))
        assert_that(config[0].pv_names_in_columns[0], is_(expected_pv_name))
        assert_that(config[0].table_line, contains_string("{0}"))

    def test_GIVEN_column_with_template_value_no_header_in_database_WHEN_generate_THEN_configuration_has_correct_pv_and_header_is_template(self):
        pv_name = "pv:name"
        expected_pv_name = pv_name + ".VAL"
        template = "{" + pv_name + "}"
        ioc_data_source = self._create_ioc_data_source(column_templates=[(pv_name, 1, template)])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].column_header_list[1], is_(template))
        assert_that(config[0].pv_names_in_columns[0], is_(expected_pv_name))
        assert_that(config[0].table_line, contains_string("{0}"))

    def test_GIVEN_column_with_empty_value_no_header_in_database_WHEN_generate_THEN_configuration_has_correct_pv_and_header_is_pv_name(self):
        pv_name = "pv:name"
        expected_pv_name = pv_name + ".VAL"
        expected_column_header = pv_name
        ioc_data_source = self._create_ioc_data_source(column_templates=[(pv_name, 1, "")])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config, has_length(1))
        assert_that(config[0].column_header_list[1], is_(expected_column_header))
        assert_that(config[0].pv_names_in_columns[0], is_(expected_pv_name))
        assert_that(config[0].table_line, contains_string("{0}"))

    def test_GIVEN_column_with_template_value_and_header_in_database_WHEN_generate_THEN_configuration_has_correct_pv_and_header(self):
        pv_name = "pv:name"
        expected_pv_name = pv_name + ".VAL"
        expected_column_header = "column name"
        ioc_data_source = self._create_ioc_data_source(
            column_templates=[("blah", 1, "{" + pv_name + "}")],
            column_headers=[("blah", 1, expected_column_header)])
        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].column_header_list, has_length(2))  # column name and time date
        assert_that(config[0].pv_names_in_columns, has_length(1))
        assert_that(config[0].column_header_list[1], is_(expected_column_header))
        assert_that(config[0].pv_names_in_columns[0], is_(expected_pv_name))
        assert_that(config[0].table_line, contains_string("{0}"))

    def test_GIVEN_columns_with_multiple_template_values_and_header_some_with_both_some_with_one_in_database_WHEN_generate_THEN_configuration_has_correct_pv_and_header(self):
        expected_pv_names = ["pv:name0.val", "pv:name1.val", "pv:name2.val", "pv:name3.val", "pv:name4.val"]
        expected_column_headers = ["column name0", "{" + expected_pv_names[1] + "}", "column_name2", "column_name3", "column_name4"]

        ioc_data_source = self._create_ioc_data_source(
            columns=[
                # template and header (split)
                (True, "blah", 4, "{" + expected_pv_names[4] + "}"),

                #  header no template
                (False, expected_pv_names[0], 0, expected_column_headers[0]),

                # template no header
                (True, "blah", 1, "{" + expected_pv_names[1] + "}"),

                # template and header (template before header
                (False, "blah", 2, expected_column_headers[2]),
                (True, "blah", 2, "{" + expected_pv_names[2] + "}"),

                # template and header (template after header)
                (True, "blah", 3, "{" + expected_pv_names[3] + "}"),
                (False, "blah", 3, expected_column_headers[3]),

                # template and header (split)
                (False, "blah", 4, expected_column_headers[4]),
            ]
        )

        db_config_builder = ArchiverAccessDatabaseConfigBuilder(ioc_data_source)

        config = db_config_builder.create()

        assert_that(config[0].column_header_list[1:], is_(expected_column_headers))
        assert_that(config[0].table_line.format(*config[0].pv_names_in_columns, time="time").split("\t")[1:], is_(expected_pv_names))

    def _create_ioc_data_source(self, ioc_name="ioc",
                                header_lines=None, header_pvs=None, header_lines_section=None,
                                trigger_pv="trigger_pv", trigger_pv_template="this_pv",
                                period_pv="period_pv", period_pv_template="this_pv", period_constant=None,
                                column_headers=None, column_templates=None, columns=None):
        """

        Args:
            ioc_name:
            header_lines:
            header_pvs: pvs associated with various header lines (for templating)
            header_lines_section:
            trigger_pv:

        Returns:

        """
        logging_data = []
        if header_lines_section is None:
            if header_lines is not None:
                for index, header_line in enumerate(header_lines):
                    try:
                        header_pv = header_pvs[index]
                    except (ValueError, TypeError):
                        header_pv = "pvname"
                    logging_data.append((header_pv, "LOG_header{0}".format(index), header_line))
        else:
            logging_data.extend(header_lines_section)

        logging_data.append((trigger_pv, "LOG_trigger", trigger_pv_template))
        if period_constant is not None:
            logging_data.append((period_pv, "LOG_period_seconds", str(period_constant)))
        else:
            logging_data.append((period_pv, "LOG_period_pv", period_pv_template))

        if column_headers is not None:
            for pv_name, index, template in column_headers:
                logging_data.append((pv_name, "LOG_column_header{0}".format(index), template))

        if column_templates is not None:
            for pv_name, index, template in column_templates:
                logging_data.append((pv_name, "LOG_column_template{0}".format(index), template))

        if columns is not None:
            for is_template, pv_name, index, template in columns:
                if is_template:
                    logging_data.append((pv_name, "LOG_column_template{0}".format(index), template))
                else:
                    logging_data.append((pv_name, "LOG_column_header{0}".format(index), template))

        data = {ioc_name: logging_data}
        ioc_data_source = Mock()
        ioc_data_source.get_pv_logging_info = Mock(return_value=data)
        return ioc_data_source
