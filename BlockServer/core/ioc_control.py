from BlockServer.epics.procserv_utils import ProcServWrapper
from server_common.utilities import print_and_log

IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')


class IocControl(object):
    """A class for starting, stopping and restarting IOCs"""
    def __init__(self, prefix, proc=ProcServWrapper()):
        """Constructor.

        Args:
            prefix (string) : The PV prefix for the instrument
            proc (ProcServWrapper, optional) : The underlying object for talking to ProcServ
        """
        self._prefix = prefix
        self._proc = proc

    def start_ioc(self, ioc):
        """Start an IOC.

        Args:
            ioc (string) : The name of the IOC
        """
        try:
            self._proc.start_ioc(self._prefix, ioc)
        except Exception as err:
            print_and_log("Could not start IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def restart_ioc(self, ioc, force=False):
        """Restart an IOC.

        Args:
            ioc (string) : The name of the IOC
            force (bool) : Force it to restart even if it is an IOC not to stop
        """
        # Check it is okay to stop it
        if not force and ioc.startswith(IOCS_NOT_TO_STOP):
            return
        try:
            self._proc.restart_ioc(self._prefix, ioc)
        except Exception as err:
            print_and_log("Could not restart IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def stop_ioc(self, ioc, force=False):
        """Stop an IOC.

        Args:
            ioc (string) : The name of the IOC
            force (bool) : Force it to stop even if it is an IOC not to stop
        """
        # Check it is okay to stop it
        if not force and ioc.startswith(IOCS_NOT_TO_STOP):
            return
        try:
            self._proc.stop_ioc(self._prefix, ioc)
        except Exception as err:
            print_and_log("Could not stop IOC %s: %s" % (ioc, str(err)), "MAJOR")

    def get_ioc_status(self, ioc):
        """Get the running status of an IOC.

        Args:
            ioc (string) : The name of the IOC

        Returns:
            string : The status of the IOC (RUNNING or SHUTDOWN)
        """
        return self._proc.get_ioc_status(self._prefix, ioc)

    def start_iocs(self, iocs):
        """ Start a number of IOCs.

        Args:
            iocs (list) : The IOCs to start
        """
        for ioc in iocs:
            self.start_ioc(ioc)

    def restart_iocs(self, iocs):
        """ Restart a number of IOCs.

        Args:
            iocs (list) : The IOCs to restart
        """
        for ioc in iocs:
            self.restart_ioc(ioc)

    def stop_iocs(self, iocs):
        """ Stop a number of IOCs.

        Args:
            iocs (list) : The IOCs to stop
        """
        for ioc in iocs:
            self.stop_ioc(ioc)

    def ioc_exists(self, ioc):
        """Checks an IOC exists.

        Args:
            ioc (string) : The name of the IOC

        Returns:
            bool : Whether the IOC exists
        """
        try:
            self.get_ioc_status(ioc)
            return True
        except:
            return False
