from __future__ import print_function, unicode_literals, division, absolute_import

import os
import sys
import subprocess
import traceback

import six
from genie_python.channel_access_exceptions import UnableToConnectToPVException, ReadAccessException
from genie_python.genie_cachannel_wrapper import CaChannelWrapper

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from RemoteIocServer.utilities import print_and_log


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
        self._recreate_gateway_config_files()
        self._restart_gateway()

    def _recreate_gateway_config_files(self):
        print_and_log("Gateway: rewriting gateway configuration file at '{}'".format(self._gateway_settings_file_path))

        if not os.path.exists(os.path.dirname(self._gateway_settings_file_path)):
            os.makedirs(os.path.dirname(self._gateway_settings_file_path))

        with open(self._gateway_settings_file_path, "w") as f:
            f.write("EVALUATION ORDER DENY, ALLOW\n")
            f.write("\n".join(self._get_alias_file_lines()))
            f.write("\n")

        with open(self._gateway_settings_file_path[:-6] + "acf", "w") as f:
            f.write(self._get_access_security_file_content())

    def _get_alias_file_lines(self):
        lines = []
        if self._remote_pv_prefix is not None:
            for ioc in self._ioc_names:
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALIAS    {local_prefix}{ioc}:\1'
                             .format(remote_prefix=self._remote_pv_prefix, local_prefix=self._local_pv_prefix, ioc=ioc))
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALLOW    GWEXT    1'
                             .format(remote_prefix=self._remote_pv_prefix, local_prefix=self._local_pv_prefix, ioc=ioc))
        return lines

    def _get_access_security_file_content(self):
        return """
HAG(allowed_write) { localhost, 127.0.0.1, """ + six.binary_type(self._get_hostname()) + """ }

ASG(DEFAULT) {
   RULE(1, READ)
   RULE(1, WRITE, TRAPWRITE)
}

ASG(GWEXT) {
    RULE(1, READ)
    RULE(1, WRITE, TRAPWRITE)
    {
        HAG(allowed_write)
    }
}

ASG(ANYBODY) {
    RULE(1, READ)
}
        """.encode("ascii")

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
        DevIocStats on any IOC publishes the hostname of the computer it's running on over channel access.
        """
        try:
            # Choose an IOC which should always be up (INSTETC) and use the deviocstats hostname record.
            name = CaChannelWrapper.get_pv_value("{}CS:IOC:INSTETC_01:DEVIOS:HOSTNAME".format(self._remote_pv_prefix),
                                                 to_string=True, timeout=5)
            print_and_log("Gateway: hostname is '{}' (from DevIocStats)".format(name))
            return name
        except (UnableToConnectToPVException, ReadAccessException) as e:
            print_and_log("Gateway: Unable to get hostname because {}.".format(e))
            return "none"
