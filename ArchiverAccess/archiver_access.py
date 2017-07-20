from datetime import datetime
from time import sleep

from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.database_config_builder import DatabaseConfigBuilder
from ArchiverAccess.ioc_data_source import IocDataSource
from ArchiverAccess.log_file_initiator import LogFileInitiatorOnPVChange, ConfigAndDependencies
from server_common.mysql_abstraction_layer import SQLAbstraction


def create_pv_monitor():
    """
    Create pv monitors based on the iocdatabase

    Returns: monitor for PV

    """
    global pv_monitor
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
    return LogFileInitiatorOnPVChange(config_and_dependencies, archiver_data_source, datetime(2017, 7, 20, 8, 0))


if __name__ == '__main__':

    pv_monitor = create_pv_monitor()

    for i in range(20):

        pv_monitor.check_write()
        sleep(1)
