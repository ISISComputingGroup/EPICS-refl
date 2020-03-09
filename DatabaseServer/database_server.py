from __future__ import print_function, absolute_import, division, unicode_literals
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

# Add root path for access to server_commons
import os
import traceback

import six
import sys
import json
import argparse
import codecs

from functools import partial
from pcaspy import Driver
from time import sleep
from threading import Thread, RLock

sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))

from DatabaseServer.exp_data import ExpData, ExpDataSource
from DatabaseServer.procserv_utils import ProcServWrapper
from DatabaseServer.options_holder import OptionsHolder
from DatabaseServer.options_loader import OptionsLoader

from server_common.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import compress_and_hex, print_and_log, set_logger, convert_to_json, \
    dehex_and_decompress, char_waveform
from server_common.channel_access_server import CAServer
from server_common.constants import IOCS_NOT_TO_STOP
from server_common.ioc_data import IOCData
from server_common.ioc_data_source import IocDataSource
from server_common.pv_names import DatabasePVNames as DbPVNames
from server_common.loggers.isis_logger import IsisLogger


set_logger(IsisLogger())

MACROS = {
    "$(MYPVPREFIX)": os.environ['MYPVPREFIX'],
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

LOG_TARGET = "DBSVR"
INFO_MSG = "INFO"
MAJOR_MSG = "MAJOR"


class DatabaseServer(Driver):
    """
    The class for handling all the static PV access and monitors etc.
    """
    def __init__(self, ca_server: CAServer, ioc_data: IOCData, exp_data: ExpData, options_folder: str,
                 blockserver_prefix: str, test_mode: bool = False):
        """
        Constructor.

        Args:
            ca_server: The CA server used for generating PVs on the fly
            ioc_data: The data source for IOC information
            exp_data: The data source for experiment information
            options_folder: The location of the folder containing the config.xml file that holds IOC options
            blockserver_prefix: The PV prefix to use
            test_mode: Enables starting the server in a mode suitable for unit tests
        """
        if not test_mode:
            super(DatabaseServer, self).__init__()

        self._blockserver_prefix = blockserver_prefix
        self._ca_server = ca_server
        self._options_holder = OptionsHolder(options_folder, OptionsLoader())
        self._pv_info = self._generate_pv_acquisition_info()
        self._iocs = ioc_data
        self._ed = exp_data

        if self._iocs is not None and not test_mode:
            # Start a background thread for keeping track of running IOCs
            self.monitor_lock = RLock()
            monitor_thread = Thread(target=self._update_ioc_monitors, args=())
            monitor_thread.daemon = True  # Daemonise thread
            monitor_thread.start()

    def _generate_pv_acquisition_info(self) -> dict:
        """
        Generates information needed to get the data for the DB PVs.

        Returns:
            Dictionary containing the information to get the information for the PVs
        """
        enhanced_info = DatabaseServer.generate_pv_info()

        def add_get_method(pv, get_function):
            enhanced_info[pv]['get'] = get_function

        add_get_method(DbPVNames.IOCS, self._get_iocs_info)
        add_get_method(DbPVNames.HIGH_INTEREST, partial(self._get_interesting_pvs, "HIGH"))
        add_get_method(DbPVNames.MEDIUM_INTEREST, partial(self._get_interesting_pvs, "MEDIUM"))
        add_get_method(DbPVNames.LOW_INTEREST, partial(self._get_interesting_pvs, "LOW"))
        add_get_method(DbPVNames.FACILITY, partial(self._get_interesting_pvs, "FACILITY"))
        add_get_method(DbPVNames.ACTIVE_PVS, self._get_active_pvs)
        add_get_method(DbPVNames.ALL_PVS, partial(self._get_interesting_pvs, ""))
        add_get_method(DbPVNames.SAMPLE_PARS, self._get_sample_par_names)
        add_get_method(DbPVNames.BEAMLINE_PARS, self._get_beamline_par_names)
        add_get_method(DbPVNames.USER_PARS, self._get_user_par_names)
        add_get_method(DbPVNames.IOCS_NOT_TO_STOP, DatabaseServer._get_iocs_not_to_stop)
        return enhanced_info

    @staticmethod
    def generate_pv_info() -> dict:
        """
        Generates information needed to construct PVs. Must be consumed by Server before
        DatabaseServer is initialized so must be static

        Returns:
            Dictionary containing the information to construct PVs
        """
        pv_size_128k = 128000
        pv_size_10k = 10000
        pv_info = {}

        for pv in [DbPVNames.IOCS, DbPVNames.HIGH_INTEREST, DbPVNames.MEDIUM_INTEREST, DbPVNames.LOW_INTEREST,
                   DbPVNames.FACILITY, DbPVNames.ACTIVE_PVS, DbPVNames.ALL_PVS, DbPVNames.IOCS_NOT_TO_STOP]:
            pv_info[pv] = char_waveform(pv_size_128k)

        for pv in [DbPVNames.SAMPLE_PARS, DbPVNames.BEAMLINE_PARS, DbPVNames.USER_PARS]:
            pv_info[pv] = char_waveform(pv_size_10k)

        return pv_info

    def get_data_for_pv(self, pv: str) -> bytes:
        """
        Get the data for the given pv name.

        Args:
            The name of the PV to get the data for.

        Return:
            The data, compressed and hexed.
        """
        data = self._pv_info[pv]['get']()
        data = compress_and_hex(six.text_type(json.dumps(data)))
        self._check_pv_capacity(pv, len(data), self._blockserver_prefix)
        return data

    def read(self, reason: str) -> str:
        """
        A method called by SimpleServer when a PV is read from the DatabaseServer over Channel Access.

        Args:
            reason: The PV that is being requested (without the PV prefix)

        Returns:
            A compressed and hexed JSON formatted string that gives the desired information based on reason.
        """
        return self.get_data_for_pv(reason) if reason in self._pv_info.keys() else self.getParam(reason)

    def write(self, reason: str, value: str) -> bool:
        """
        A method called by SimpleServer when a PV is written to the DatabaseServer over Channel Access.

        Args:
            reason: The PV that is being requested (without the PV prefix)
            value: The data being written to the 'reason' PV

        Returns:
            True
        """
        try:
            if reason == 'ED:RBNUMBER:SP':
                self._ed.update_experiment_id(value)
            elif reason == 'ED:USERNAME:SP':
                self._ed.update_username(dehex_and_decompress(value.encode('utf-8')).decode('utf-8'))
        except Exception as e:
            value = compress_and_hex(convert_to_json("Error: " + str(e)))
            print_and_log(str(e), MAJOR_MSG)
        # store the values
        self.setParam(reason, value)
        return True

    def _update_ioc_monitors(self) -> None:
        """
        Updates all the PVs that hold information on the IOCS and their associated PVs.
        """
        while True:
            if self._iocs is not None:
                self._iocs.update_iocs_status()
                for pv in [DbPVNames.IOCS, DbPVNames.HIGH_INTEREST, DbPVNames.MEDIUM_INTEREST, DbPVNames.FACILITY,
                           DbPVNames.ACTIVE_PVS, DbPVNames.ALL_PVS]:
                    encoded_data = self.get_data_for_pv(pv)
                    # No need to update monitors if data hasn't changed
                    if not self.getParam(pv) == encoded_data:
                        self.setParam(pv, encoded_data)
                # Update them
                with self.monitor_lock:
                    self.updatePVs()
            sleep(1)

    def _check_pv_capacity(self, pv: str, size: int, prefix: str) -> None:
        """
        Check the capacity of a PV and write to the log if it is too small.
        
        Args:
            pv: The PV that is being requested (without the PV prefix)
            size: The required size
            prefix: The PV prefix
        """
        if size > self._pv_info[pv]['count']:
            print_and_log("Too much data to encode PV {0}. Current size is {1} characters but {2} are required"
                          .format(prefix + pv, self._pv_info[pv]['count'], size),
                          MAJOR_MSG, LOG_TARGET)

    def _get_iocs_info(self) -> dict:
        iocs = self._iocs.get_iocs()
        options = self._options_holder.get_config_options()
        for iocname in iocs.keys():
            if iocname in options:
                iocs[iocname].update(options[iocname])
        return iocs

    def _get_pvs(self, get_method: callable, replace_pv_prefix: bool, *get_args: list) -> list:
        """
        Method to get pv data using the given method called with the given arguments and optionally remove instrument
        prefixes from pv names.

        Args:
            get_method: The method used to get pv data.
            replace_pv_prefix: True to remove pv prefixes, False if not.
            get_args: The arguments to be applied to get_method.
        Returns:
            a list of names of pvs.
        """
        if self._iocs is not None:
            pv_data = get_method(*get_args)
            if replace_pv_prefix:
                pv_data = [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in pv_data]
            return pv_data
        else:
            return []

    def _get_interesting_pvs(self, level) -> list:
        """
        Gets interesting pvs of the current instrument.

        Args:
            level: The level of high interesting pvs, can be high, low, medium or facility. If level is an empty
                   string, it returns all interesting pvs of all levels.
        Returns:
            a list of names of pvs with given level of interest.
        """
        return self._get_pvs(self._iocs.get_interesting_pvs, False, level)

    def _get_active_pvs(self) -> list:
        """
        Gets all pvs belonging to IOCs that are currently running on the current instrument.

        Returns:
             a list of names of pvs.
        """
        return self._get_pvs(self._iocs.get_active_pvs, False)

    def _get_sample_par_names(self) -> list:
        """
        Returns the sample parameters from the database, replacing the MYPVPREFIX macro.

        Returns:
            A list of sample parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._iocs.get_sample_pars, True)

    def _get_beamline_par_names(self) -> list:
        """
        Returns the beamline parameters from the database, replacing the MYPVPREFIX macro.

        Returns:
            A list of beamline parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._iocs.get_beamline_pars, True)

    def _get_user_par_names(self) -> list:
        """
        Returns the user parameters from the database, replacing the MYPVPREFIX macro.

        Returns:
            A list of user parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._iocs.get_user_pars, True)

    @staticmethod
    def _get_iocs_not_to_stop() -> list:
        """
        Get the IOCs that are not to be stopped.

        Returns: 
            A list of IOCs not to stop
        """
        return IOCS_NOT_TO_STOP


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-bs', '--blockserver_prefix', nargs=1, type=str,
                        default=[MACROS["$(MYPVPREFIX)"]+'CS:'],
                        help='The prefix for PVs served by the blockserver(default=%MYPVPREFIX%CS:)')

    parser.add_argument('-od', '--options_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration options(default=current directory)')

    args = parser.parse_args()

    BLOCKSERVER_PREFIX = args.blockserver_prefix[0]
    if not BLOCKSERVER_PREFIX.endswith(':'):
        BLOCKSERVER_PREFIX += ":"
    BLOCKSERVER_PREFIX = BLOCKSERVER_PREFIX.replace('%MYPVPREFIX%', MACROS["$(MYPVPREFIX)"])
    print_and_log("BLOCKSERVER PREFIX = %s" % BLOCKSERVER_PREFIX, INFO_MSG, LOG_TARGET)

    OPTIONS_DIR = os.path.abspath(args.options_dir[0])
    print_and_log("OPTIONS DIRECTORY = %s" % OPTIONS_DIR, INFO_MSG, LOG_TARGET)
    if not os.path.isdir(os.path.abspath(OPTIONS_DIR)):
        # Create it then
        os.makedirs(os.path.abspath(OPTIONS_DIR))

    SERVER = CAServer(BLOCKSERVER_PREFIX)
    SERVER.createPV(BLOCKSERVER_PREFIX, DatabaseServer.generate_pv_info())
    SERVER.createPV(MACROS["$(MYPVPREFIX)"], ExpData.EDPV)

    # Initialise IOC database connection
    try:
        ioc_data = IOCData(IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb")), ProcServWrapper(),
                           MACROS["$(MYPVPREFIX)"])
        print_and_log("Connected to IOCData database", INFO_MSG, LOG_TARGET)
    except Exception as e:
        ioc_data = None
        print_and_log("Problem initialising IOCData DB connection: {}".format(traceback.format_exc()),
                      MAJOR_MSG, LOG_TARGET)

    # Initialise experimental database connection
    try:
        exp_data = ExpData(MACROS["$(MYPVPREFIX)"], ExpDataSource())
        print_and_log("Connected to experimental details database", INFO_MSG, LOG_TARGET)
    except Exception as e:
        exp_data = None
        print_and_log("Problem connecting to experimental details database: {}".format(traceback.format_exc()),
                      MAJOR_MSG, LOG_TARGET)

    DRIVER = DatabaseServer(SERVER, ioc_data, exp_data, OPTIONS_DIR, BLOCKSERVER_PREFIX)

    # Process CA transactions
    while True:
        try:
            SERVER.process(0.1)
        except Exception as err:
            print_and_log(traceback.format_exc(), MAJOR_MSG)
            break
