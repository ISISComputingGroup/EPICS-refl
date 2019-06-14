import os
import subprocess

from utilities import print_and_log


class GateWay(object):
    def __init__(self, gateway_settings_file_path, local_pv_prefix):
        self._instrument = None
        self._ioc_names = []
        self._local_pv_prefix = local_pv_prefix
        self._gateway_settings_file_path = gateway_settings_file_path

        self._reapply_gateway_settings()

    def set_instrument(self, instrument):
        print_and_log("Gateway: instrument changed from {} to {}".format(self._instrument, instrument))
        self._instrument = instrument
        self._reapply_gateway_settings()

    def set_ioc_list(self, iocs):
        print_and_log("Gateway: ioc list changed from {} to {}".format(str(self._ioc_names), str(iocs)))
        self._ioc_names = iocs
        self._reapply_gateway_settings()

    def _reapply_gateway_settings(self):
        self._recreate_gateway_file()
        self._restart_gateway()

    def _recreate_gateway_file(self):
        print_and_log("Rewriting gateway configuration file at '{}'".format(self._gateway_settings_file_path))
        with open(self._gateway_settings_file_path, "w") as f:
            f.write("EVALUATION ORDER ALLOW, DENY\n")
            f.writelines(self._get_alias_file_lines())
            f.write("\n")

    def _get_alias_file_lines(self):
        if self._instrument is None:
            return []
        else:
            lines = []
            for ioc in self._ioc_names:
                lines.append(r'IN:{instrument}:{ioc}:\(.*\)    ALIAS    {local_pv_prefix}{ioc}:\1'
                             .format(local_pv_prefix=self._local_pv_prefix, ioc=ioc, instrument=self._instrument))
            return lines

    def _restart_gateway(self):
        print_and_log("Restarting gateway")
        subprocess.call(os.path.join("C:\\", "Instrument", "Apps", "EPICS", "gateway", "start_remoteioc_server.bat"))
