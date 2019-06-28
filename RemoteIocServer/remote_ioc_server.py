from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import sys
import os
import traceback

from pcaspy import SimpleServer, Driver

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from RemoteIocServer.config_monitor import ConfigurationMonitor
from RemoteIocServer.gateway import GateWay
from RemoteIocServer.pvdb import STATIC_PV_DATABASE, PvNames
from RemoteIocServer.utilities import print_and_log
from BlockServer.core.ioc_control import IocControl


DEFAULT_GATEWAY_START_BAT = os.path.join("C:\\", "Instrument", "Apps", "EPICS", "gateway", "start_remoteioc_server.bat")


class RemoteIocListDriver(Driver):
    def __init__(self, ioc_names, pv_prefix, gateway_settings_path, gateway_restart_script_path):
        super(RemoteIocListDriver, self).__init__()
        # TODO: don't hardcode.
        self._instrument = None

        self._ioc_controller = IocControl(pv_prefix)

        self._iocs = ioc_names

        self._gateway = GateWay(
            local_pv_prefix=pv_prefix,
            gateway_settings_file_path=gateway_settings_path,
            gateway_restart_script_path=gateway_restart_script_path
        )
        self._gateway.set_instrument(self._instrument)
        self._gateway.set_ioc_list(ioc_names)

        # TODO: don't hardcode
        self._configuration_monitor = ConfigurationMonitor("TE:NDW1799:".format(self._instrument),
                                                           restart_iocs_callback=self.restart_all_iocs)

        self.updatePVs()

    def write(self, reason, value):
        print_and_log("RemoteIocListDriver: Processing PV write for reason {}".format(reason))
        if reason == PvNames.INSTRUMENT_SP:
            self.set_instrument(value)
        else:
            print_and_log("RemoteIocListDriver: Could not write to PV '{}': not known".format(reason), "MAJOR")

        # Update PVs after any write.
        self.updatePVs()

    def read(self, reason):
        print_and_log("RemoteIocListDriver: Processing PV read for reason {}".format(reason))
        self.updatePVs()  # Update PVs before any read so that they are up to date.

        if reason == PvNames.INSTRUMENT_SP or reason == PvNames.INSTRUMENT:
            return self._instrument if self._instrument is not None else "NONE"
        else:
            print_and_log("RemoteIocListDriver: Could not read from PV '{}': not known".format(reason), "MAJOR")

    def set_instrument(self, new_instrument):
        print_and_log("RemoteIocListDriver: setting instrument to {} (old: {})"
                      .format(new_instrument, self._instrument))
        self._instrument = new_instrument
        # TODO: don't hardcode
        self._configuration_monitor.set_remote_pv_prefix("TE:NDW1799:")
        self.restart_all_iocs()
        self._gateway.set_instrument(new_instrument)
        self.updatePVs()
        print_and_log("RemoteIocListDriver: Finished setting instrument to {}".format(self._instrument))

    def restart_all_iocs(self):
        print_and_log("RemoteIocListDriver: Restarting all IOCs")
        for ioc_name in self._iocs:
            self._ioc_controller.restart_ioc(ioc_name, force=True, restart_alarm_server=False)


def serve_forever(pv_prefix, subsystem_prefix, ioc_names, gateway_settings_path, gateway_restart_script_path):
    server = SimpleServer()

    server.createPV("{}{}".format(pv_prefix, subsystem_prefix).encode('ascii'), STATIC_PV_DATABASE)

    # Looks like it does nothing, but this creates *and automatically registers* the driver
    # (via metaclasses in pcaspy). See declaration of DriverType in pcaspy/driver.py for details
    # of how it achieves this.
    RemoteIocListDriver(ioc_names, pv_prefix, gateway_settings_path, gateway_restart_script_path)

    try:
        while True:
            server.process(0.1)
    except Exception:
        print_and_log(traceback.format_exc())
        raise


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Runs a remote IOC server.",
    )

    parser.add_argument("--ioc_names", type=str, nargs="+", default=[],
                        help="The list of IOCS to be managed by this remote IOC server. The names should be in the"
                             " same format as the names in the IOC list.")
    parser.add_argument("--pv_prefix", required=True, type=str,
                        help="The PV prefix of this instrument.")
    parser.add_argument("--subsystem_prefix", type=str,
                        default="REMIOC:",
                        help="The subsystem prefix to use for this remote IOC server")
    parser.add_argument("--gateway_settings_path", type=str,
                        default=r"C:\instrument\settings\gwremoteioc.pvlist",
                        help="The path to the gateway pvlist file to generate")
    parser.add_argument("--gateway_restart_script_path", type=str,
                        default=DEFAULT_GATEWAY_START_BAT,
                        help="The path to the script to call to restart the remote ioc gateway")

    args = parser.parse_args()

    serve_forever(
        args.pv_prefix,
        args.subsystem_prefix,
        args.ioc_names,
        args.gateway_settings_path,
        args.gateway_restart_script_path
    )


if __name__ == "__main__":
    main()
