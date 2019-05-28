import argparse
import sys
import os

from pcaspy import SimpleServer, Driver

from global_settings import read_globals_file, write_globals_file
from pvdb import STATIC_PV_DATABASE, PvNames, pvdb_for_ioc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import print_and_log
from BlockServer.core.ioc_control import IocControl


class RemoteIoc(object):
    def __init__(self, ioc_control, name):
        self.name = name
        self._ioc_control = ioc_control
        self.restart_required = False

    def start(self):
        self._ioc_control.start_ioc(self.name)

    def stop(self):
        self._ioc_control.stop_ioc(self.name, force=True)
        self.restart_required = False

    def restart(self):
        self._ioc_control.restart_ioc(self.name, force=True)
        self.restart_required = False


class RemoteIocListDriver(Driver):
    def __init__(self, ioc_names, pv_prefix):
        super(RemoteIocListDriver, self).__init__()
        self._instrument = "NDW1799"

        self._ioc_controller = IocControl(pv_prefix)

        self._iocs = {name: RemoteIoc(self._ioc_controller, name) for name in ioc_names}

    def write(self, reason, value):
        print("Processing PV write for reason {}".format(reason))
        if reason == PvNames.INSTRUMENT_SP:
            self.set_instrument(value)
        elif self._is_ioc_specific_request(reason, "START"):
            self._iocs[reason.split(":")[0]].start()
        elif self._is_ioc_specific_request(reason, "STOP"):
            self._iocs[reason.split(":")[0]].stop()
        elif self._is_ioc_specific_request(reason, "RESTART"):
            self._iocs[reason.split(":")[0]].restart()
        elif reason == PvNames.WRITE_GLOBALS:
            write_globals_file(value)
            self.require_restarts_for_all_iocs()
        else:
            print_and_log("Could not write to PV '{}': not known".format(reason), "MAJOR")

        # Update PVs after any write.
        self.updatePVs()

    def read(self, reason):
        print("Processing PV read for reason {}".format(reason))
        if reason == PvNames.INSTRUMENT_SP or reason == PvNames.INSTRUMENT:
            return self._instrument
        elif self._is_ioc_specific_request(reason, "START") \
                or self._is_ioc_specific_request(reason, "STOP") \
                or self._is_ioc_specific_request(reason, "RESTART"):
            return 0
        elif reason == PvNames.READ_GLOBALS or reason == PvNames.WRITE_GLOBALS:
            return read_globals_file()
        else:
            print_and_log("Could not read from PV '{}': not known".format(reason), "MAJOR")

    def _is_ioc_specific_request(self, reason, paramname):
        try:
            return reason.split(":")[0] in self._iocs and reason.split(":")[1] == paramname
        except (ValueError, TypeError, IndexError):
            return False

    def set_instrument(self, new_instrument):
        self._instrument = new_instrument
        self.require_restarts_for_all_iocs()

    def require_restarts_for_all_iocs(self):
        for remote_ioc in self._iocs.values():
            remote_ioc.restart_required = True


def serve_forever(pv_prefix, subsystem_prefix, ioc_names):
    server = SimpleServer()

    pvdb = STATIC_PV_DATABASE.copy()
    for ioc_db in [pvdb_for_ioc(name) for name in ioc_names]:
        pvdb.update(ioc_db)

    server.createPV("{}{}".format(pv_prefix, subsystem_prefix), pvdb)

    # Looks like it does nothing, but this creates *and automatically registers* it
    # (via metaclasses in pcaspy). See declaration of DriverType in pcaspy/driver.py for details
    # of how it achieves this.
    RemoteIocListDriver(ioc_names, pv_prefix)

    try:
        while True:
            server.process(0.1)
    except Exception:
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Runs a remote IOC server.",
    )

    parser.add_argument("--ioc_names", type=str, nargs="+", default=None,
                        help="The list of IOCS to be managed by this remote IOC server. The names should be in the"
                             " same format as the names in the IOC list.")
    parser.add_argument("--pv_prefix", required=True, type=str,
                        help="The PV prefix of this instrument.")
    parser.add_argument("--subsystem_prefix", type=str, default="REMIOC:",
                        help="The subsystem prefix to use for this remote IOC server")

    args = parser.parse_args()

    serve_forever(args.pv_prefix, args.subsystem_prefix, args.ioc_names)


if __name__ == "__main__":
    main()
