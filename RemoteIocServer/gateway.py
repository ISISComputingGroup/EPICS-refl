from __future__ import print_function, unicode_literals, division, absolute_import

import os
import sys
import subprocess
import textwrap
import threading
import traceback

import six

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from RemoteIocServer.utilities import print_and_log, get_hostname_from_prefix, THREADPOOL


GATEWAY_FILESYSTEM_WRITE_LOCK = threading.RLock()
GATEWAY_RESTART_LOCK = threading.RLock()


class GateWay(object):
    """
    Class representing the EPICS remote IOC gateway.
    """

    def __init__(self, gateway_pvlist_file_path, gateway_acf_path, gateway_restart_script_path, local_pv_prefix):
        self._remote_pv_prefix = None
        self._ioc_names = []
        self._local_pv_prefix = local_pv_prefix
        self._gateway_pvlist_file_path = gateway_pvlist_file_path
        self._gateway_acf_file_path = gateway_acf_path
        self._gateway_restart_script_path = gateway_restart_script_path

        self._reapply_gateway_settings()

    def set_remote_pv_prefix(self, remote_pv_prefix):
        """
        Sets the remote PV prefix (i.e. the prefix of the NDX machine). Will cause gateways to reload.

        Args:
            remote_pv_prefix: the prefix of the remote machine to observe (e.g. IN:DEMO: )
        """
        print_and_log("Gateway: instrument changed from {} to {}".format(self._remote_pv_prefix, remote_pv_prefix))
        self._remote_pv_prefix = remote_pv_prefix
        self._reapply_gateway_settings()

    def set_ioc_list(self, iocs):
        """
        Changes the list of IOCS which this gateway is aliasing.

        Args:
            iocs: the new list of IOC names to observe
        """
        print_and_log("Gateway: ioc list changed from {} to {}".format(str(self._ioc_names), str(iocs)))
        self._ioc_names = iocs
        self._reapply_gateway_settings()

    def _reapply_gateway_settings(self):
        self._recreate_gateway_config_files()
        THREADPOOL.submit(lambda: self._restart_gateway())

    def _recreate_gateway_config_files(self):
        with GATEWAY_FILESYSTEM_WRITE_LOCK:
            print_and_log("Gateway: rewriting gateway configuration file at '{}'".format(self._gateway_pvlist_file_path))

            if not os.path.exists(os.path.dirname(self._gateway_pvlist_file_path)):
                os.makedirs(os.path.dirname(self._gateway_pvlist_file_path))

            with open(self._gateway_pvlist_file_path, "w") as f:
                f.write("EVALUATION ORDER DENY, ALLOW\n")
                f.write("\n".join(self._get_alias_file_lines()))
                f.write("\n")

            with open(self._gateway_acf_file_path, "w") as f:
                f.write(self._get_access_security_file_content())

    def _get_alias_file_lines(self):
        lines = []
        if self._remote_pv_prefix is not None:
            for ioc in self._ioc_names:
                lines.append(r'{remote_prefix}{ioc}:\(.*\)    ALIAS    {local_prefix}{ioc}:\1'
                             .format(remote_prefix=self._remote_pv_prefix, local_prefix=self._local_pv_prefix, ioc=ioc))
        return lines

    def _get_access_security_file_content(self):
        hostname = get_hostname_from_prefix(self._remote_pv_prefix)
        return textwrap.dedent("""\
            HAG(allowed_write) { localhost, 127.0.0.1, """ + six.binary_type(hostname) + """ }
            
            ASG(DEFAULT) {
               RULE(1, READ)
               RULE(1, WRITE, TRAPWRITE)
               {
                   HAG(allowed_write)
               }
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
            """.encode("ascii") if hostname is not None else "")

    def _restart_gateway(self):
        with GATEWAY_RESTART_LOCK:
            print_and_log("Gateway: restarting")
            try:
                with open(os.devnull, "w") as devnull:
                    status = subprocess.call(self._gateway_restart_script_path, stdout=devnull, stderr=devnull)
                print_and_log("Gateway: restart complete (exit code: {})".format(status))
            except subprocess.CalledProcessError:
                print_and_log("Gateway: restart failed (path to script: {})".format(self._gateway_restart_script_path))
                print_and_log(traceback.format_exc())
