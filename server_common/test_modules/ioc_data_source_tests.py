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
from server_common.mysql_abstraction_layer import DatabaseError


class SQLAbstractionStubForIOC(object):
    def __init__(self, query_return):
        self.query_return = []
        for ioc, values in query_return.iteritems():
            for value in values:
                pv_info = [ioc]
                pv_info.extend(value)
                self.query_return.append(pv_info)

    def query(self, sql, param=None):
        return self.query_return


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
        data_source=IocDataSource(mysql_abstraction_layer)

        result = data_source.get_pv_logging_info()

        assert_that(result, is_(expected_result))

    def test_GIVEN_database_error_WHEN_get_values_THEN_error(self):
        mysql_abstraction_layer = SQLAbstractionStubForIOC({})
        mysql_abstraction_layer.query = Mock(side_effect=DatabaseError("DB Error"))
        data_source=IocDataSource(mysql_abstraction_layer)

        assert_that(calling(data_source.get_pv_logging_info), raises(DatabaseError))
