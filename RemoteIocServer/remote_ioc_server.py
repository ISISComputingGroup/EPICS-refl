from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import sys
import os
import traceback
import six

from pcaspy import SimpleServer, Driver

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from RemoteIocServer.config_monitor import ConfigurationMonitor
from RemoteIocServer.gateway import GateWay
from RemoteIocServer.pvdb import STATIC_PV_DATABASE, PvNames
from RemoteIocServer.utilities import print_and_log, THREADPOOL, read_startup_file
from BlockServer.core.ioc_control import IocControl
from BlockServer.core.file_path_manager import FILEPATH_MANAGER
from server_common.autosave import AutosaveFile


AUTOSAVE_REMOTE_PREFIX_NAME = "remote_pv_prefix"


DEFAULT_GATEWAY_START_BAT = os.path.join(os.getenv("EPICS_KIT_ROOT"), "gateway", "start_remoteioc_server.bat")


def _error_handler(func):
    @six.wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            print_and_log(traceback.format_exc())
    return _wrapper


class RemoteIocListDriver(Driver):
    """
    A driver for a list of remote IOCs
    """

    def __init__(self, pv_prefix, gateway_pvlist_path, gateway_acf_path, gateway_restart_script_path):
        """
        A driver for a list of remote IOCs

        Args:
            ioc_names: a list of ioc names
            pv_prefix: the pv prefix
            gateway_pvlist_path: the path to the gateway pv list
            gateway_acf_path: the path to the gateway ACF file
            gateway_restart_script_path: the path to the script to restart the gateway
        """
        super(RemoteIocListDriver, self).__init__()
        self._autosave = AutosaveFile(service_name="RemoteIocServer", file_name="settings")
        self._remote_pv_prefix = self._autosave.read_parameter(AUTOSAVE_REMOTE_PREFIX_NAME, None)

        self._ioc_controller = IocControl(pv_prefix)

        self._iocs = read_startup_file()

        self._gateway = GateWay(
            local_pv_prefix=pv_prefix,
            gateway_pvlist_file_path=gateway_pvlist_path,
            gateway_acf_path=gateway_acf_path,
            gateway_restart_script_path=gateway_restart_script_path
        )
        self._gateway.set_remote_pv_prefix(self._remote_pv_prefix)
        self._gateway.set_ioc_list(self._iocs)

        self._configuration_monitor = ConfigurationMonitor(
            local_pv_prefix=pv_prefix,
            restart_iocs_callback=self.restart_all_iocs
        )
        self._configuration_monitor.set_remote_pv_prefix(self._remote_pv_prefix)

        self.updatePVs()

    @_error_handler
    def write(self, reason, value):
        """
        Handle write to PV
        Args:
            reason: PV to set value of
            value: Value to set
        """
        print_and_log("RemoteIocListDriver: Processing PV write for reason {}".format(reason))
        if reason == PvNames.INSTRUMENT:
            self.set_remote_pv_prefix(value)
        else:
            print_and_log("RemoteIocListDriver: Could not write to PV '{}': not known".format(reason), "MAJOR")

        # Update PVs after any write.
        self.updatePVs()

    @_error_handler
    def read(self, reason):
        """
        Handle read of PV
        Args:
            reason: PV to read value of
        """
        print_and_log("RemoteIocListDriver: Processing PV read for reason {}".format(reason))
        self.updatePVs()  # Update PVs before any read so that they are up to date.

        if reason == PvNames.INSTRUMENT:
            return six.binary_type(self._remote_pv_prefix if self._remote_pv_prefix is not None else "NONE")
        else:
            print_and_log("RemoteIocListDriver: Could not read from PV '{}': not known".format(reason), "MAJOR")

    def set_remote_pv_prefix(self, remote_pv_prefix):
        """
        Set the pv prefix for the remote server.
        Args:
            remote_pv_prefix: new prefix to use

        Returns:

        """
        print_and_log("RemoteIocListDriver: setting instrument to {} (old: {})"
                      .format(remote_pv_prefix, self._remote_pv_prefix))
        self._remote_pv_prefix = remote_pv_prefix
        self._autosave.write_parameter(AUTOSAVE_REMOTE_PREFIX_NAME, remote_pv_prefix)

        THREADPOOL.submit(self._configuration_monitor.set_remote_pv_prefix, remote_pv_prefix)
        THREADPOOL.submit(self.restart_all_iocs)
        THREADPOOL.submit(self._gateway.set_remote_pv_prefix, remote_pv_prefix)
        self.updatePVs()
        print_and_log("RemoteIocListDriver: Finished setting instrument to {}".format(self._remote_pv_prefix))

    def restart_all_iocs(self):
        """
        Restart all the IOCs on the remote server.
        """
        print_and_log("RemoteIocListDriver: Restarting all IOCs")
        for ioc_name in self._iocs:
            if self._ioc_controller.get_ioc_status(ioc_name) == "RUNNING":
                self._ioc_controller.restart_ioc(ioc_name, force=True, restart_alarm_server=False)
            else:
                self._ioc_controller.start_ioc(ioc_name, restart_alarm_server=False)


def serve_forever(pv_prefix, subsystem_prefix, gateway_pvlist_path, gateway_acf_path,
                  gateway_restart_script_path):
    """
    Server the PVs for the remote ioc server
    Args:
        pv_prefix: prefex for the pvs
        subsystem_prefix: prefix for the PVs published by the remote IOC server
        gateway_pvlist_path: The path to the gateway pvlist file to generate
        gateway_acf_path: The path to the gateway access security file to generate
        gateway_restart_script_path: The path to the script to call to restart the remote ioc gateway

    Returns:

    """
    server = SimpleServer()

    server.createPV("{}{}".format(pv_prefix, subsystem_prefix).encode('ascii'), STATIC_PV_DATABASE)

    # Looks like it does nothing, but this creates *and automatically registers* the driver
    # (via metaclasses in pcaspy). See declaration of DriverType in pcaspy/driver.py for details
    # of how it achieves this.
    RemoteIocListDriver(pv_prefix, gateway_pvlist_path, gateway_acf_path, gateway_restart_script_path)

    try:
        while True:
            server.process(0.1)
    except Exception:
        print_and_log(traceback.format_exc())
        raise


def main():
    """
    Parse the command line argumnts and run the remote IOC server.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Runs a remote IOC server.",
    )

    parser.add_argument("--pv_prefix", required=True, type=six.text_type,
                        help="The PV prefix of this instrument.")
    parser.add_argument("--subsystem_prefix", type=six.text_type,
                        default="REMIOC:",
                        help="The subsystem prefix to use for this remote IOC server")
    parser.add_argument("--gateway_pvlist_path", type=six.text_type,
                        default=os.path.normpath(
                            os.path.join(os.getenv("ICPCONFIGROOT"), "AccessSecurity", "gwremoteioc.pvlist")),
                        help="The path to the gateway pvlist file to generate")
    parser.add_argument("--gateway_acf_path", type=six.text_type,
                        default=os.path.normpath(
                            os.path.join(os.getenv("ICPCONFIGROOT"), "AccessSecurity", "gwremoteioc.acf")),
                        help="The path to the gateway access security file to generate")
    parser.add_argument("--gateway_restart_script_path", type=six.text_type,
                        default=DEFAULT_GATEWAY_START_BAT,
                        help="The path to the script to call to restart the remote ioc gateway")

    args = parser.parse_args()

    FILEPATH_MANAGER.initialise(os.path.normpath(os.getenv("ICPCONFIGROOT")), "", "")

    serve_forever(
        args.pv_prefix,
        args.subsystem_prefix,
        args.gateway_pvlist_path,
        args.gateway_acf_path,
        args.gateway_restart_script_path
    )


if __name__ == "__main__":
    main()
