import os
import sys

from server_common.ioc_data_source import IocDataSource
from server_common.mysql_abstraction_layer import SQLAbstraction


def register_ioc_start(ioc_name, pv_database=None, prefix=None):
    """
    A helper function to register the start of an ioc.
    Args:
        ioc_name: name of the ioc to start
        pv_database: doctionary of pvs in the iov
        prefix: prefix of pvs in this ioc
    """

    exepath = sys.argv[0]
    if pv_database is None:
        pv_database = {}
    if prefix is None:
        prefix = "none"

    ioc_data_source = IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb"))
    ioc_data_source.insert_ioc_start(ioc_name, os.getpid(), exepath, pv_database, prefix)
