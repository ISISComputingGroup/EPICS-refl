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
Module for accessing the archiver
"""
import os
import signal


from time import sleep

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.database_config_builder import DatabaseConfigBuilder
from ArchiverAccess.log_file_initiator import LogFileInitiatorOnPVChange, ConfigAndDependencies
from ArchiverAccess.time_last_active import TimeLastActive
from server_common.ioc_data import IocDataSource
from server_common.mysql_abstraction_layer import SQLAbstraction

finish = False
"""Finish the program"""


def create_pv_monitor():
    """
    Create pv monitors based on the iocdatabase

    Returns: monitor for PV

    """
    archive_mysql_abstraction_layer = SQLAbstraction("archive", "report", "$report")
    ioc_mysql_abstraction_layer = SQLAbstraction("iocdb", "iocdb", "$iocdb")
    archiver_data_source = ArchiverDataSource(archive_mysql_abstraction_layer)
    ioc_data_source = IocDataSource(ioc_mysql_abstraction_layer)
    configs_from_db = DatabaseConfigBuilder(ioc_data_source).create()
    config_and_dependencies = []
    for config in configs_from_db:
        archive_data_file_creator = ArchiveDataFileCreator(config, archiver_data_source)
        config_and_dependencies.append(
            ConfigAndDependencies(config, archive_data_file_creator)
        )
    return LogFileInitiatorOnPVChange(config_and_dependencies, archiver_data_source, TimeLastActive())


def signal_handler(signal, frame):
    """
    Handle interrupt singal nicely
    Args:
        signal: signal
        frame: frame in which it was issued

    Returns:

    """
    global finish
    finish = True

if __name__ == '__main__':

    pv_monitor = create_pv_monitor()

    signal.signal(signal.SIGINT, signal_handler)
    while not finish:
        pv_monitor.check_write()
        try:
            sleep(1)
        except IOError:
            # signal interrupts sleep
            pass
