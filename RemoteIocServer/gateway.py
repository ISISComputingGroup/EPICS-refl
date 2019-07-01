from __future__ import print_function, unicode_literals, division, absolute_import

import os
import subprocess
import traceback

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
        self._recreate_gateway_file()
        self._restart_gateway()

    def _recreate_gateway_file(self):
        print_and_log("Gateway: rewriting gateway configuration file at '{}'".format(self._gateway_settings_file_path))
        with open(self._gateway_settings_file_path, "w") as f:
            f.write("EVALUATION ORDER ALLOW, DENY\n")
            f.writelines(self._get_alias_file_lines())
            f.write("\n")

    def _get_alias_file_lines(self):
        lines = []
        if self._remote_pv_prefix is not None:
            for ioc in self._ioc_names:
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALIAS    {local_prefix}{ioc}:\1'
                             .format(remote_prefix=self._remote_pv_prefix, local_prefix=self._local_pv_prefix, ioc=ioc))
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
