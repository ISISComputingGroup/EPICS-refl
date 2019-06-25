from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import sys
import os

from pcaspy import SimpleServer, Driver

from config_monitor import ConfigurationMonitor
from gateway import GateWay
from remote_ioc import RemoteIoc
from global_settings import read_globals_file, write_globals_file
from pvdb import STATIC_PV_DATABASE, PvNames, pvdb_for_ioc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from utilities import print_and_log
from BlockServer.core.ioc_control import IocControl


class RemoteIocListDriver(Driver):
    def __init__(self, ioc_names, pv_prefix, gateway_settings_path):
        super(RemoteIocListDriver, self).__init__()
        # TODO: don't hardcode.
        self._instrument = "NDW1799"

        self._ioc_controller = IocControl(pv_prefix)

        self._iocs = {name: RemoteIoc(self._ioc_controller, name) for name in ioc_names}

        self._gateway = GateWay(local_pv_prefix=pv_prefix, gateway_settings_file_path=gateway_settings_path)
        self._gateway.set_instrument(self._instrument)
        self._gateway.set_ioc_list(ioc_names)

        self.configuration_monitor = ConfigurationMonitor("TE:NDW1799:".format(self._instrument),
                                                          restart_iocs_callback=self.restart_all_iocs)

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
            self.restart_all_iocs()
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

        self.updatePVs()

    def _is_ioc_specific_request(self, reason, paramname):
        try:
            return reason.split(":")[0] in self._iocs and reason.split(":")[1] == paramname
        except (ValueError, TypeError, IndexError):
            return False

    def set_instrument(self, new_instrument):
        self._instrument = new_instrument
        self.restart_all_iocs()
        self._gateway.set_instrument(new_instrument)
        # TODO: don't hardcode this...
        self.configuration_monitor.set_remote_pv_prefix("TE:NDW1799:")

    def restart_all_iocs(self):
        for ioc in self._iocs.values():
            ioc.restart()


def serve_forever(pv_prefix, subsystem_prefix, ioc_names, gateway_settings_path):
    server = SimpleServer()

    pvdb = STATIC_PV_DATABASE.copy()
    for ioc_db in [pvdb_for_ioc(name) for name in ioc_names]:
        pvdb.update(ioc_db)

    server.createPV("{}{}".format(pv_prefix, subsystem_prefix), pvdb)

    # Looks like it does nothing, but this creates *and automatically registers* it
    # (via metaclasses in pcaspy). See declaration of DriverType in pcaspy/driver.py for details
    # of how it achieves this.
    RemoteIocListDriver(ioc_names, pv_prefix, gateway_settings_path)

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
    parser.add_argument("--gateway_settings_path", type=str, default=r"C:\instrument\settings\gwremoteioc.pvlist",
                        help="The path to the gateway pvlist file to generate")

    args = parser.parse_args()

    serve_forever(args.pv_prefix, args.subsystem_prefix, args.ioc_names, args.gateway_settings_path)


if __name__ == "__main__":
    main()
