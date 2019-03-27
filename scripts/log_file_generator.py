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
Script for generating a log file from the archive.
"""
import argparse
from datetime import datetime, timedelta

import os
import sys

try:
    from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.archive_access_configuration import ArchiveAccessConfigBuilder
from server_common.mysql_abstraction_layer import SQLAbstraction

finish = False
"""Finish the program"""


def not_readonly(path):
    """
    Final function of the log
    Args:
        path: path of file

    """
    print("Created log file {}".format(path))


def create_log(headers, columns, time_period, default_field, filename_template="default.log", host="127.0.0.1"):
    """
    Create pv monitors based on the iocdatabase

    Returns: monitor for PV

    """
    archive_mysql_abstraction_layer = SQLAbstraction("archive", "report", "$report", host=host)
    archiver_data_source = ArchiverDataSource(archive_mysql_abstraction_layer)

    config_builder = ArchiveAccessConfigBuilder(filename_template, default_field=default_field)
    for header in headers:
        config_builder.header(header)

    for column_header, column_template in columns:
        config_builder.table_column(column_header, column_template)

    adfc = ArchiveDataFileCreator(config_builder.build(), archiver_data_source, filename_template,
                                  make_file_readonly=not_readonly)
    adfc.write_complete_file(time_period)


if __name__ == '__main__':
    description = "Create a log file from the archive. E.g. python ArchiverAccess\log_file_generator.py " \
                  "--start_time 2018-01-10T09:00:00 --point_count 1000 --delta_time 1 --host ndximat " \
                  "--filename_template log{start_time}.csv  " \
                  "MOT0101 IN:IMAT:MOT:MTR0101.RBV MOT0102 IN:IMAT:MOT:MTR0102.RBV"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--point_count", "-c", type=int, help="Number of sample points", required=True)
    parser.add_argument("--start_time", "-s", help="Start time for sample iso date, 2018-12-20T16:01:02", required=True)
    parser.add_argument("--delta_time", "-d", type=float, help="The time between points in seconds", required=True)
    parser.add_argument("--host", default="localhost", help="Host to get data from defaults to localhost")
    parser.add_argument("--filename_template", "-f", default="log.log",
                        help="Filename template to use for the log file.")
    parser.add_argument("--default_field", default="VAL",
                        help="If the pv has no field add this field to it.")

    parser.add_argument("header_and_pvs", nargs="+",
                        help="A header followed by the name for each pv appearing in the data")

    args = parser.parse_args()

    try:
        data_start_time = datetime.strptime(args.start_time, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError) as ex:
        print("Can not interpret date '{}' error: {}".format(args.start_time, ex))
        exit(1)

    the_time_period = ArchiveTimePeriod(data_start_time, timedelta(seconds=args.delta_time), args.point_count)
    header_line = ["Data from {}".format(args.host)]

    column_defs = []
    header = None
    for header_and_pv in args.header_and_pvs:
        if header is None:
            header = header_and_pv
        else:
            column_defs.append((header, "{{{}}}".format(header_and_pv)))
            header = None

    if header is not None:
        print("There must be at least one pv and every pv must have a header")
        exit(2)

    create_log(
        header_line,
        column_defs,
        the_time_period,
        filename_template=args.filename_template,
        host=args.host,
        default_field=args.default_field)
