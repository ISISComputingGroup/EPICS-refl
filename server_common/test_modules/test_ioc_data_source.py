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
from hamcrest import *
from mock import Mock

from server_common.ioc_data_source import IocDataSource
from server_common.mysql_abstraction_layer import DatabaseError, AbstratSQLCommands


class SQLAbstractionStubForIOC(AbstratSQLCommands):
    """Testing stub."""
    def __init__(self, query_return):
        self.sql_param = []
        self.sql = []
        self.query_return = []
        for ioc, values in query_return.items():
            for value in values:
                pv_info = [ioc]
                pv_info.extend(value)
                self.query_return.append(pv_info)

    def _execute_command(self, command, is_query, bound_variables):
        self.sql.append(command)
        self.sql_param.append(bound_variables)
        if is_query:
            return self.query_return
        return None


class TestIocDataSource(unittest.TestCase):
    def test_GIVEN_1_logging_annotations_request_WHEN_get_values_THEN_value_returned_grouped_by_ioc(self):
        expected_result = {"ioc1": [["pv1", "log_header1", "an interesting value"]]}

        mysql_abstraction_layer = SQLAbstractionStubForIOC(expected_result)
        data_source = IocDataSource(mysql_abstraction_layer)

        result = data_source.get_pv_logging_info()

        assert_that(result, is_(expected_result))

    def test_GIVEN_no_logging_annotations_request_WHEN_get_values_THEN_empty_dictionary_returned(self):
        expected_result = {}

        mysql_abstraction_layer = SQLAbstractionStubForIOC(expected_result)
        data_source = IocDataSource(mysql_abstraction_layer)

        result = data_source.get_pv_logging_info()

        assert_that(result, is_(expected_result))

    def test_GIVEN_multiple_logging_annotations_over_multiple_iocs_WHEN_get_values_THEN_values_returned_grouped_by_ioc(self):
        expected_result = {
            "ioc1": [["pv1", "log_header1", "an interesting value"],
                     ["pv1", "log_header2", "an interesting value"],
                     ["pv3", "log_trigger", "an interesting value"]],
            "ioc2": [["pv5", "log_header1", "an interesting value"]],
            "ioc3": [["pv1", "log_header1", "an interesting value"]]
        }

        mysql_abstraction_layer = SQLAbstractionStubForIOC(expected_result)
        data_source = IocDataSource(mysql_abstraction_layer)

        result = data_source.get_pv_logging_info()

        assert_that(result, is_(expected_result))

    def test_GIVEN_database_error_WHEN_get_values_THEN_error(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        mysql_abstraction_layer.query = Mock(side_effect=DatabaseError("DB Error"))
        data_source = IocDataSource(mysql_abstraction_layer)

        assert_that(calling(data_source.get_pv_logging_info), raises(DatabaseError))

    def test_GIVEN_ioc_with_pvs_WHEN_pvdump_THEN_calls_are_made_to_delete_previous_entries(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        data_source = IocDataSource(mysql_abstraction_layer)

        data_source.insert_ioc_start("name", 12, "path", {}, "prefix")

        assert_that(mysql_abstraction_layer.sql[0], contains_string("DELETE FROM iocrt"))
        assert_that(mysql_abstraction_layer.sql[1], contains_string("DELETE FROM pvs"))

    def test_GIVEN_ioc_with_pvs_WHEN_pvdump_has_database_error_THEN_no_exception_raised(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        mysql_abstraction_layer.update = Mock(side_effect=DatabaseError("DB Error"))
        data_source = IocDataSource(mysql_abstraction_layer)

        data_source.insert_ioc_start("name", 12, "path", {}, "prefix")

    def test_GIVEN_ioc_with_pvs_WHEN_pvdump_THEN_calls_are_made_to_add_ioc_started(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        data_source = IocDataSource(mysql_abstraction_layer)

        data_source.insert_ioc_start("name", 12, "path", {}, "prefix")

        assert_that(mysql_abstraction_layer.sql[2], contains_string("INSERT INTO iocrt"))

    def test_GIVEN_ioc_with_pvs_WHEN_pvdump_THEN_calls_are_made_to_add_pvs_with_correct_types_and_names_and_default_type_is_float(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        data_source = IocDataSource(mysql_abstraction_layer)

        expected_type1 = "int"
        expected_type2 = "float"
        prefix = "prefix"
        pv_name_1 = "pv_name_1"
        pv_name_2 = "pv_name_2"
        expected_name1 = "{}{}".format(prefix, pv_name_1)
        expected_name2 = "{}{}".format(prefix, pv_name_2)
        pvs = {pv_name_1: {"type": expected_type1},
               pv_name_2: {}}

        iocname = "name"
        data_source.insert_ioc_start(iocname, 12, "path", pvs, prefix)

        for sql in mysql_abstraction_layer.sql[3:5]:
            assert_that(sql, contains_string("INSERT INTO pvs"))

        assert_that(mysql_abstraction_layer.sql_param[3:5], contains_inanyorder(
                (expected_name1, expected_type1, "", iocname),
                (expected_name2, expected_type2, "", iocname)))

    def test_GIVEN_ioc_with_pvs_with_pv_info_WHEN_pvdump_THEN_calls_are_made_to_add_pv_info_with_correct_pv_names_info_names_and_values(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        data_source = IocDataSource(mysql_abstraction_layer)
        name1 = "archive"
        value1 = ""
        name2 = "INTEREST"
        value2 = "HIGH"
        prefix = "prefix"
        pv_name = "pv_name"
        expected_name1 = "{}{}".format(prefix, pv_name)
        pvs = {pv_name: {"info_field": {name1: value1, name2: value2}}}

        data_source.insert_ioc_start("name", 12, "path", pvs, prefix)

        for sql in mysql_abstraction_layer.sql[4:]:
            assert_that(sql, contains_string("INSERT INTO pvinfo"))

        assert_that(mysql_abstraction_layer.sql_param[4:], contains_inanyorder(
                (expected_name1, name1, value1),
                (expected_name1, name2, value2)))
