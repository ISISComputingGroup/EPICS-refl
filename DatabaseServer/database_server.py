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

IOCDB = 'iocdb'
IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')

MACROS = {
    "$(MYPVPREFIX)": os.environ['MYPVPREFIX'],
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT']
}

PVDB = {
    'IOCS': {
        # Handled by the monitor thread
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
    'PVS:INTEREST:HIGH': {
        # Handled by the monitor thread
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'PVS:INTEREST:MEDIUM': {
        # Handled by the monitor thread
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'PVS:ACTIVE': {
        # Handled by the monitor thread
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'PVS:ALL': {
        # Handled by the monitor thread
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
    'SAMPLE_PARS': {
        'type': 'char',
        'count': 10000,
        'value': [0],
    },
    'BEAMLINE_PARS': {
        'type': 'char',
        'count': 10000,
        'value': [0],
    },
    'IOCS_NOT_TO_STOP': {
        'type': 'char',
        'count': 16000,
        'value': [0],
    },
}


class DatabaseServer(Driver):
    """The class for handling all the static PV access and monitors etc.
    """
    def __init__(self, ca_server, dbid, options_folder, test_mode=False):
        """Constructor.

        Args:
            ca_server (CAServer) : The CA server used for generating PVs on the fly
            dbid (string) : The id of the database that holds IOC information.
            options_folder (string) : The location of the folder containing the config.xml file that holds IOC options
        """
        if test_mode:
            ps = MockProcServWrapper()
        else:
            super(DatabaseServer, self).__init__()
            ps = ProcServWrapper()
        self._ca_server = ca_server
        self._options_holder = OptionsHolder(options_folder, OptionsLoader())

        # Initialise database connection
        try:
            self._db = IOCData(dbid, ps, MACROS["$(MYPVPREFIX)"])
            self._db.check_db_okay()
            print_and_log("Connected to database", "INFO", "DBSVR")
        except Exception as err:
            self._db = None
            print_and_log("Problem initialising DB connection: %s" % err, "MAJOR", "DBSVR")

        # Initialise experimental database connection
        try:
            self._ed = ExpData(MACROS["$(MYPVPREFIX)"])
            self._ed.check_db_okay()
            print_and_log("Connected to experimental details database", "INFO", "DBSVR")
        except Exception as err:
            self._ed = None
            print_and_log("Problem connecting to experimental details database: %s" % err, "MAJOR", "DBSVR")

        if self._db is not None and not test_mode:
            # Start a background thread for keeping track of running IOCs
            self.monitor_lock = RLock()
            monitor_thread = Thread(target=self.update_ioc_monitors, args=())
            monitor_thread.daemon = True  # Daemonise thread
            monitor_thread.start()

    def read(self, reason):
        """A method called by SimpleServer when a PV is read from the DatabaseServer over Channel Access.

        Args:
            reason (string) : The PV that is being requested (without the PV prefix)

        Returns:
            string : A compressed and hexed JSON formatted string that gives the desired information based on reason.
        """
        if reason == 'SAMPLE_PARS':
            value = self.encode4return(self.get_sample_par_names())
        elif reason == 'BEAMLINE_PARS':
            value = self.encode4return(self.get_beamline_par_names())
        elif reason == "IOCS_NOT_TO_STOP":
            value = self.encode4return(IOCS_NOT_TO_STOP)
        else:
            value = self.getParam(reason)
        return value

    def write(self, reason, value):
        """A method called by SimpleServer when a PV is written to the DatabaseServer over Channel Access.

        Args:
            reason (string) : The PV that is being requested (without the PV prefix)
            value (string) : The data being written to the 'reason' PV

        Returns:
            bool : True
        """
        status = True
        try:
            if reason == 'ED:RBNUMBER:SP':
                #print_and_log("Updating to use experiment ID: " + value, "INFO", "DBSVR")
                self._ed.updateExperimentID(value)
            elif reason == 'ED:USERNAME:SP':
                self._ed.updateUsername(dehex_and_decompress(value))
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def update_ioc_monitors(self):
        """Updates all the PVs that hold information on the IOCS and their associated PVs
        """
        while True:
            if self._db is not None:
                self._db.update_iocs_status()
                self.setParam("IOCS", self.encode4return(self._get_iocs_info()))
                self.setParam("PVS:ALL", self.encode4return(self._get_interesting_pvs("")))
                self.setParam("PVS:ACTIVE", self.encode4return(self._get_active_pvs()))
                self.setParam("PVS:INTEREST:HIGH", self.encode4return(self._get_interesting_pvs("HIGH")))
                self.setParam("PVS:INTEREST:MEDIUM", self.encode4return(self._get_interesting_pvs("MEDIUM")))
                self._update_individual_interesting_pvs()
                # Update them
                with self.monitor_lock:
                    self.updatePVs()
            sleep(1)

    def encode4return(self, data):
        """Converts data to JSON, compresses it and converts it to hex.

        Args:
            data (string) : The data to encode

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

    def _get_interesting_pvs(self, level, ioc=None):
        if self._db is not None:
            return self._db.get_interesting_pvs(level, ioc)
        else:
            return list()

    def _get_active_pvs(self):
        if self._db is not None:
            return self._db.get_active_pvs()
        else:
            return list()

    def _update_individual_interesting_pvs(self):
        for level in ["HIGH", "MEDIUM"]:
            for iocname in self._db.get_iocs().keys():
                pvs = self._get_interesting_pvs(level, iocname)
                self._ca_server.updatePV("INTERESTING_PVS:" + iocname + ":" + level, self.encode4return(pvs))

    def get_sample_par_names(self):
        """Returns the sample parameters from the database, replacing the MYPVPREFIX macro

        Returns:
            list : A list of sample parameter names, an empty list if the database does not exist
        """
        if self._db is not None:
            return [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in self._db.get_sample_pars()]
        else:
            return list()

    def get_beamline_par_names(self):
        """Returns the beamline parameters from the database, replacing the MYPVPREFIX macro

        Returns:
            list : A list of beamline parameter names, an empty list if the database does not exist
        """
        if self._db is not None:
            return [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in self._db.get_beamline_pars()]
        else:
            return list()

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
    print_and_log("FACILITY = %s" % FACILITY, "INFO", "DBSVR")

    BLOCKSERVER_PREFIX = args.blockserver_prefix[0]
    if not BLOCKSERVER_PREFIX.endswith(':'):
        BLOCKSERVER_PREFIX += ":"
    BLOCKSERVER_PREFIX = BLOCKSERVER_PREFIX.replace('%MYPVPREFIX%', MACROS["$(MYPVPREFIX)"])
    print_and_log("BLOCKSERVER PREFIX = %s" % BLOCKSERVER_PREFIX, "INFO", "DBSVR")

    OPTIONS_DIR = os.path.abspath(args.options_dir[0])
    print_and_log("OPTIONS DIRECTORY = %s" % OPTIONS_DIR, "INFO", "DBSVR")
    if not os.path.isdir(os.path.abspath(OPTIONS_DIR)):
        # Create it then
        os.makedirs(os.path.abspath(OPTIONS_DIR))

    SERVER = CAServer(BLOCKSERVER_PREFIX)
    SERVER.createPV(BLOCKSERVER_PREFIX, PVDB)
    SERVER.createPV(MACROS["$(MYPVPREFIX)"], ExpData.EDPV)
    DRIVER = DatabaseServer(SERVER, IOCDB, OPTIONS_DIR)

    # Process CA transactions
    while True:
        SERVER.process(0.1)
