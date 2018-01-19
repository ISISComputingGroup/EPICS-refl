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
"""
Module for creating a log file
"""
from datetime import datetime, timedelta

from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.archive_access_configuration import ArchiveAccessConfigBuilder
from server_common.mysql_abstraction_layer import SQLAbstraction

finish = False
"""Finish the program"""


def create_log(headers, columns, time_period, filename_template="default.log", host="127.0.0.1"):
    """
    Create pv monitors based on the iocdatabase

    Returns: monitor for PV

    """
    archive_mysql_abstraction_layer = SQLAbstraction("archive", "report", "$report", host=host)
    archiver_data_source = ArchiverDataSource(archive_mysql_abstraction_layer)

    config_builder = ArchiveAccessConfigBuilder(filename_template)
    for header in headers:
        config_builder.header(header)

    for column_header, column_template in columns:
        config_builder.table_column(column_header, column_template)

    adfc = ArchiveDataFileCreator(config_builder.build(), archiver_data_source)
    adfc.write_complete_file(time_period)

if __name__ == '__main__':
    sample_size = 10000000
    the_time_period = ArchiveTimePeriod(datetime(2017, 9, 8, 15, 00), timedelta(seconds=0.1), sample_size)
    header_line = ["Test IMAT"]
    column_defs = [
        ("MOT 0201", "{IN:LARMOR:MOT:MTR0201.RBV}"),
        ("MOT 0208", "{IN:LARMOR:MOT:MTR0208.RBV}")]
    create_log(
        header_line,
        column_defs,
        the_time_period,
        filename_template="larmor_motors.log".format(sample_size),
        host="ndxlarmor")
