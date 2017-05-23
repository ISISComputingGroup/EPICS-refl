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
import sys
sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))


# Standard imports
from pcaspy import Driver
from time import sleep
import argparse
from server_common.utilities import compress_and_hex, print_and_log, set_logger, convert_to_json, dehex_and_decompress
from server_common.channel_access_server import CAServer
from ioc_data import IOCData
from exp_data import ExpData
import json
from threading import Thread, RLock
from procserv_utils import ProcServWrapper
from options_holder import OptionsHolder
from options_loader import OptionsLoader
from mocks.mock_procserv_utils import MockProcServWrapper

MACROS = {
    "$(MYPVPREFIX)": os.environ['MYPVPREFIX'],
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

LOG_TARGET = "DBSVR"
INFO_MSG = "INFO"
MAJOR_MSG = "MAJOR"

class DatabaseServer(Driver):
    """The class for handling all the static PV access and monitors etc.
    """
    def __init__(self, ca_server, dbid, options_folder, test_mode=False):
        """Constructor.

        Args:
            ca_server (CAServer): The CA server used for generating PVs on the fly
            dbid (string): The id of the database that holds IOC information.
            options_folder (string): The location of the folder containing the config.xml file that holds IOC options
        """
        pass
        if test_mode:
            ps = MockProcServWrapper()
        else:
            super(DatabaseServer, self).__init__()
            ps = ProcServWrapper()
        self._ca_server = ca_server
        self._options_holder = OptionsHolder(options_folder, OptionsLoader())

        self._pvdb = self._create_pv_database()

        # Initialise database connection
        try:
            self._db = IOCData(dbid, ps, MACROS["$(MYPVPREFIX)"])
            print_and_log("Connected to database", INFO_MSG, LOG_TARGET)
        except Exception as err:
            self._db = None
            print_and_log("Problem initialising DB connection: %s" % err, MAJOR_MSG, LOG_TARGET)

        # Initialise experimental database connection
        try:
            self._ed = ExpData(MACROS["$(MYPVPREFIX)"])
            print_and_log("Connected to experimental details database", INFO_MSG, LOG_TARGET)
        except Exception as err:
            self._ed = None
            print_and_log("Problem connecting to experimental details database: %s" % err, MAJOR_MSG, LOG_TARGET)

        if self._db is not None and not test_mode:
            # Start a background thread for keeping track of running IOCs
            self.monitor_lock = RLock()
            monitor_thread = Thread(target=self._update_ioc_monitors, args=())
            monitor_thread.daemon = True  # Daemonise thread
            monitor_thread.start()

    def _create_pv_database(self):
        pv_size_64k = 64000
        pv_size_10k = 10000

        # Helper to consistently create pvs
        def create_pvdb_entry(count, get_function):
            return {
                'type': 'char',
                'count' : count,
                'value' : [0],
                'get' : get_function
        }

        return {
            'IOCS': create_pvdb_entry(pv_size_64k, self._get_iocs_info),
            'PVS:INTEREST:HIGH': create_pvdb_entry(pv_size_64k, self._get_high_interest_pvs),
            'PVS:INTEREST:MEDIUM': create_pvdb_entry(pv_size_64k, self._get_medium_interest_pvs),
            'PVS:INTEREST:FACILITY': create_pvdb_entry(pv_size_64k, self._get_facility_pvs),
            'PVS:ACTIVE': create_pvdb_entry(pv_size_64k, self._get_active_pvs),
            'PVS:ALL': create_pvdb_entry(pv_size_64k, self._get_all_pvs),
            'SAMPLE_PARS': create_pvdb_entry(pv_size_10k, self.get_sample_par_names),
            'BEAMLINE_PARS': create_pvdb_entry(pv_size_10k, self._get_beamline_par_names),
            'USER_PARS': create_pvdb_entry(pv_size_10k, self._get_user_par_names),
            'IOCS_NOT_TO_STOP': create_pvdb_entry(pv_size_64k, DatabaseServer._get_iocs_not_to_stop),
        }

    def process(self, interval):
        """
        Tell the CA server to process requests
        
        Args:
            interval (float): How long the processing loop will take in seconds
        """
        self._ca_server.process(interval)

    def create_server_pv(self, prefix, pvs=None):
        """
        Instruct the CA server to create a set of PVs
        
        Args:
            prefix (string): The PV prefix to prepend to the PVs
            pvs (dict): A dictionary of PVs and associated metadata used to create PVs
        """
        self._ca_server.createPV(prefix, pvs if pvs is not None else self._pvdb)

    def read(self, reason):
        """A method called by SimpleServer when a PV is read from the DatabaseServer over Channel Access.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)

        Returns:
            string : A compressed and hexed JSON formatted string that gives the desired information based on reason.
        """
        if reason in self._pvdb.keys():
            encoded_data = self._encode_for_return(self._pvdb[reason]['get']())
            self._check_pv_capacity(reason, len(encoded_data), BLOCKSERVER_PREFIX)
        else:
            encoded_data = self.getParam(reason)
        return encoded_data

    def write(self, reason, value):
        """A method called by SimpleServer when a PV is written to the DatabaseServer over Channel Access.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)
            value (string): The data being written to the 'reason' PV

        Returns:
            bool : True
        """
        status = True
        try:
            if reason == 'ED:RBNUMBER:SP':
                #print_and_log("Updating to use experiment ID: " + value, INFO_MSG, LOG_LOCATION)
                self._ed.updateExperimentID(value)
            elif reason == 'ED:USERNAME:SP':
                self._ed.updateUsername(dehex_and_decompress(value))
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), MAJOR_MSG)
        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def _update_ioc_monitors(self):
        """Updates all the PVs that hold information on the IOCS and their associated PVs
        """
        while True:
            if self._db is not None:
                self._db.update_iocs_status()
                for pv in ["IOCS", "PVS:ALL", "PVS:ACTIVE", "PVS:INTEREST:HIGH", "PVS:INTEREST:MEDIUM",
                           "PVS:INTEREST:FACILITY"]:
                    encoded_data = self._encode_for_return(self._pvdb[pv]['get']())
                    DatabaseServer._check_pv_capacity(pv, len(encoded_data), BLOCKSERVER_PREFIX)
                    self.setParam(pv, encoded_data)
                # Update them
                with self.monitor_lock:
                    self.updatePVs()
            sleep(1)

    def _check_pv_capacity(self, pv, size, prefix):
        """
        Check the capacity of a PV and write to the log if it is too small
        
        Args:
            pv (string): The PV that is being requested (without the PV prefix)
            size (int): The required size
            prefix (string): The PV prefix
        """
        if size > self._pvdb[pv]['count']:
            print_and_log("Too much data to encode PV {0}. Current size is {1} characters but {2} are required"
                          .format(prefix + pv, self._pvdb[pv]['count'], size),
                          MAJOR_MSG, LOG_TARGET)

    def _encode_for_return(self, data):
        """Converts data to JSON, compresses it and converts it to hex.

        Args:
            data (string): The data to encode

        Returns:
            string : The encoded data
        """
        return compress_and_hex(json.dumps(data).encode('ascii', 'replace'))

    def _get_iocs_info(self):
        iocs = self._db.get_iocs()
        options = self._options_holder.get_config_options()
        for iocname in iocs.keys():
            if iocname in options:
                iocs[iocname].update(options[iocname])
        return iocs

    def _get_pvs(self, get_method, *get_args):
        if self._db is not None:
            return [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in get_method(get_args)]
        else:
            return list()

    def _get_high_interest_pvs(self, ioc=None):
        return self._get_interesting_pvs("HIGH", ioc)

    def _get_medium_interest_pvs(self, ioc=None):
        return self._get_interesting_pvs("MEDIUM", ioc)

    def _get_facility_pvs(self, ioc=None):
        return self._get_interesting_pvs("FACILITY", ioc)

    def _get_all_pvs(self, ioc=None):
        return self._get_interesting_pvs("", ioc)

    def _get_interesting_pvs(self, level, ioc=None):
        return self._get_pvs(self._db.get_interesting_pvs, (level, ioc))

    def _get_active_pvs(self):
        return self._get_pvs(self._db.get_active_pvs)

    def get_sample_par_names(self):
        """Returns the sample parameters from the database, replacing the MYPVPREFIX macro

        Returns:
            list : A list of sample parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._db.get_sample_pars)

    def _get_beamline_par_names(self):
        """Returns the beamline parameters from the database, replacing the MYPVPREFIX macro

        Returns:
            list : A list of beamline parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._db.get_beamline_pars)

    def _get_user_par_names(self):
        """Returns the user parameters from the database, replacing the MYPVPREFIX macro

        Returns:
            list : A list of user parameter names, an empty list if the database does not exist
        """
        return self._get_pvs(self._db.get_user_pars)

    @staticmethod
    def _get_iocs_not_to_stop():
        """
        Returns: 
            list: A list of IOCs not to stop
        """
        return ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-bs', '--blockserver_prefix', nargs=1, type=str, default=[MACROS["$(MYPVPREFIX)"]+'CS:BLOCKSERVER:'],
                        help='The prefix for PVs served by the blockserver(default=%MYPVPREFIX%CS:BLOCKSERVER:)')

    parser.add_argument('-od', '--options_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration options(default=current directory)')

    parser.add_argument('-f', '--facility', nargs=1, type=str, default=['ISIS'],
                        help='Which facility is this being run for (default=ISIS)')

    args = parser.parse_args()

    FACILITY = args.facility[0]
    if FACILITY == "ISIS":
        from server_common.loggers.isis_logger import IsisLogger
        set_logger(IsisLogger())
    print_and_log("FACILITY = %s" % FACILITY, INFO_MSG, LOG_TARGET)

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

    DRIVER = DatabaseServer(CAServer(BLOCKSERVER_PREFIX), "iocdb", OPTIONS_DIR)
    DRIVER.create_server_pv(BLOCKSERVER_PREFIX)
    DRIVER.create_server_pv(MACROS["$(MYPVPREFIX)"], ExpData.EDPV)

    # Process CA transactions
    while True:
        try:
            DRIVER.process(0.1)
        except Exception as err:
            print_and_log(err,MAJOR_MSG)
            break

    DRIVER.close()
