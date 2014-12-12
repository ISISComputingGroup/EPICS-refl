from pcaspy import Driver, SimpleServer
import os
from time import sleep
import argparse
from utilities import compress_and_hex, dehex_and_decompress, print_and_log
from sqlite_wrapper import SqliteWrapper
import json
from threading import Thread, RLock
from procserv_utils import ProcServWrapper
from options_holder import OptionsHolder
from options_loader import OptionsLoader

IOCDB = 'iocs.sq3'
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
    },
    'PVS:INTEREST:HIGH': {
        'type': 'char',
        'count': 64000,
    },
    'PVS:INTEREST:MEDIUM': {
        'type': 'char',
        'count': 64000,
    },
    'SAMPLE_PARS': {
        'type': 'char',
        'count': 10000,
    },
    'BEAMLINE_PARS': {
        'type': 'char',
        'count': 10000,
    },
    'IOCS_NOT_TO_STOP': {
        'type': 'char',
        'count': 16000,
    },
}


class DatabaseServer(Driver):
    def __init__(self, db_file, options_folder):
        super(DatabaseServer, self).__init__()
        self._options_holder = OptionsHolder(options_folder, OptionsLoader())

        # Initialise database connection
        try:
            self._db = SqliteWrapper(MACROS["$(EPICS_KIT_ROOT)"] + db_file, ProcServWrapper(), MACROS["$(MYPVPREFIX)"])
            self._db.check_db_okay()
            print_and_log("Connected to database", "INFO", "DBSVR")
        except Exception as err:
            self._db = None
            print_and_log("Problem initialising DB connection: %s" % err, "ERROR", "DBSVR")

        if self._db is not None:
            # Start a background thread for keeping track of running IOCs
            self.monitor_lock = RLock()
            monitor_thread = Thread(target=self.update_ioc_monitors, args=())
            monitor_thread.daemon = True  # Daemonise thread
            monitor_thread.start()

    def read(self, reason):
        # This is called by CA
        if reason == 'PVS:INTEREST:HIGH':
            value = self.encode4return(self._get_interesting_pvs("HIGH"))
        elif reason == 'PVS:INTEREST:MEDIUM':
            value = self.encode4return(self._get_interesting_pvs("MEDIUM"))
        elif reason == 'SAMPLE_PARS':
            value = self.encode4return(self.get_sample_par_names())
        elif reason == 'BEAMLINE_PARS':
            value = self.encode4return(self.get_beamline_par_names())
        elif reason == "IOCS_NOT_TO_STOP":
            value = self.encode4return(IOCS_NOT_TO_STOP)
        else:
            value = self.getParam(reason)
        return value

    def write(self, reason, value):
        # This is called by CA
        status = True
        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def update_ioc_monitors(self):
        while True:
            if self._db is not None:
                self._db.update_iocs_status()
                self.setParam("IOCS", self.encode4return(self._get_iocs_info()))
                # Update them
                with self.monitor_lock:
                    self.updatePVs()
            sleep(1)

    def encode4return(self, data):
        return compress_and_hex(json.dumps(data).encode('ascii', 'replace'))

    def _get_iocs_info(self):
        iocs = self._db.get_iocs()
        options = self._options_holder.get_config_options_string()
        for iocname in iocs.keys():
            if iocname in options:
                iocs[iocname].update(options[iocname])
        return iocs

    def _get_interesting_pvs(self, level, ioc=None):
        if self._db is not None:
            return self._db.get_interesting_pvs(level, ioc)
        else:
            return list()

    def get_sample_par_names(self):
        if self._db is not None:
            return [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in self._db.get_sample_pars()]
        else:
            return list()

    def get_beamline_par_names(self):
        if self._db is not None:
            return [p.replace(MACROS["$(MYPVPREFIX)"], "") for p in self._db.get_beamline_pars()]
        else:
            return list()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-bs', '--blockserver_prefix', nargs=1, type=str, default=['%MYPVPREFIX%CS:BLOCKSERVER:'],
                        help='The prefix for PVs served by the blockserver(default=%MYPVPREFIX%CS:BLOCKSERVER:)')

    parser.add_argument('-od', '--options_dir', nargs=1, type=str, default=['.'],
                        help='The directory from which to load the configuration options(default=current directory)')

    args = parser.parse_args()

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

    SERVER = SimpleServer()
    SERVER.createPV(BLOCKSERVER_PREFIX, PVDB)
    DRIVER = DatabaseServer(IOCDB, OPTIONS_DIR)

    # Process CA transactions
    while True:
        SERVER.process(0.1)