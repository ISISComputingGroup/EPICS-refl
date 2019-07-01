from __future__ import print_function, unicode_literals, division, absolute_import

import json
import os
import sys
import subprocess
import traceback

from genie_python.channel_access_exceptions import UnableToConnectToPVException, ReadAccessException
from genie_python.genie_cachannel_wrapper import CaChannelWrapper

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from RemoteIocServer.utilities import print_and_log
from server_common.utilities import dehex_and_decompress


class GateWay(object):
    def __init__(self, gateway_settings_file_path, gateway_restart_script_path, local_pv_prefix):
        self._remote_pv_prefix = None
        self._ioc_names = []
        self._local_pv_prefix = local_pv_prefix
        self._gateway_settings_file_path = gateway_settings_file_path
        self._gateway_restart_script_path = gateway_restart_script_path

        self._reapply_gateway_settings()

    def set_remote_pv_prefix(self, remote_pv_prefix):
        print_and_log("Gateway: instrument changed from {} to {}".format(self._remote_pv_prefix, remote_pv_prefix))
        self._remote_pv_prefix = remote_pv_prefix
        self._reapply_gateway_settings()

    def set_ioc_list(self, iocs):
        print_and_log("Gateway: ioc list changed from {} to {}".format(str(self._ioc_names), str(iocs)))
        self._ioc_names = iocs
        self._reapply_gateway_settings()

    def _reapply_gateway_settings(self):
        self._recreate_gateway_file()
        self._restart_gateway()

    def _recreate_gateway_file(self):
        print_and_log("Gateway: rewriting gateway configuration file at '{}'".format(self._gateway_settings_file_path))
        with open(self._gateway_settings_file_path, "w") as f:
            f.write("EVALUATION ORDER ALLOW, DENY\n")
            f.write("\n".join(self._get_alias_file_lines()))
            f.write("\n")

    def _get_alias_file_lines(self):
        lines = []
        if self._remote_pv_prefix is not None:
            for ioc in self._ioc_names:
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALIAS    {local_prefix}{ioc}:\1'
                             .format(remote_prefix=self._remote_pv_prefix, local_prefix=self._local_pv_prefix, ioc=ioc))
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    DENY'
                             .format(remote_prefix=self._remote_pv_prefix, ioc=ioc))
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALLOW FROM {hostname}'
                             .format(remote_prefix=self._remote_pv_prefix, ioc=ioc, hostname=self._get_hostname()))
        return lines

    def _restart_gateway(self):
        print_and_log("Gateway: restarting")
        try:
            with open(os.devnull, "w") as devnull:
                status = subprocess.call(self._gateway_restart_script_path, stdout=devnull, stderr=devnull)
            print_and_log("Gateway: restart complete (exit code: {})".format(status))
        except subprocess.CalledProcessError:
            print_and_log("Gateway: restart failed (path to script: {})".format(self._gateway_restart_script_path))
            print_and_log(traceback.format_exc())

    def _get_hostname(self):
        """
        The gateway access files depend on hostname, but we only know the PV prefix and don't want to have to pass both.

        We can try:
        - Getting the hostname direct from the instrument using a PV (won't work if server is down)
        - Getting the hostname from the instrument list based on the PV prefix (won't work if not an instrument)
        - If neither of the above work, guess (and print a warning) based on the PV prefix.

        Between the approaches above we have covered all of the common cases.
        """
        return self._get_host_from_prefix_using_deviocstats() \
            or self._get_host_from_prefix_using_instlist() \
            or self._guess_hostname_from_prefix()

    def _get_host_from_prefix_using_deviocstats(self):
        """
        DevIocStats on any IOC publishes the hostname of the computer it's running on over channel access.
        """
        try:
            # Choose an IOC which should always be up (INSTETC) and use the deviocstats hostname record.
            name = CaChannelWrapper.get_pv_value("{}CS:IOC:INSTETC_01:DEVIOS:HOSTNAME".format(self._remote_pv_prefix),
                                                 to_string=True, timeout=5)
            print_and_log("Gateway: hostname is '{}' (from DevIocStats)".format(name))
            return name
        except (UnableToConnectToPVException, ReadAccessException) as e:
            print_and_log("Gateway: Unable to use DevIocStats to get hostname because {}.".format(e))

    def _get_host_from_prefix_using_instlist(self):
        """
        Looks in the global instrument list for an instrument who's PV prefix matches the one we're looking for, and
        return the hostname.
        """
        try:
            raw_instrument_list = dehex_and_decompress(
                CaChannelWrapper.get_pv_value("CS:INSTLIST", to_string=True, timeout=5))
            instrument_list = json.loads(raw_instrument_list)

            for inst in instrument_list:
                if inst["pvPrefix"] == self._remote_pv_prefix:
                    print_and_log("Gateway: hostname is '{}' (from instrument list)".format(inst["hostName"]))
                    return inst["hostName"]
            else:
                print_and_log("Gateway: Unable to use inst list to get hostname: not in instrument list")
        except Exception as e:
            print_and_log("Gateway: Unable to use inst list to get hostname because {}.".format(e))

    def _guess_hostname_from_prefix(self):
        """
        Guess the hostname of a PC given it's PV prefix
        """
        try:
            name = self._remote_pv_prefix.split(":")[1]
            print_and_log("Gateway: guessing that hostname is '{}'.".format(name))
            return name
        except (TypeError, ValueError, IndexError) as e:
            print_and_log("Gateway: unable to guess hostname from pv prefix because {}".format(e))
