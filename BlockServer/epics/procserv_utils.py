from server_common.channel_access import caget, caput
from server_common.utilities import print_and_log


class ProcServWrapper(object):
    """A wrapper for accessing some of the functionality of ProcServ."""

    @staticmethod
    def generate_prefix(prefix, ioc):
        """Generate the PV prefix for an IOCs ProcServ.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC

        Returns:
            (string) : The PV prefix
        """
        return "%sCS:PS:%s" % (prefix, ioc)

    def start_ioc(self, prefix, ioc):
        """Starts the specified IOC.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC
        """
        print_and_log("Starting IOC %s" % ioc)
        caput(self.generate_prefix(prefix, ioc) + ":START", 1)

    def stop_ioc(self, prefix, ioc):
        """Stops the specified IOC.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC
        """
        print_and_log("Stopping IOC %s" % ioc)
        caput(self.generate_prefix(prefix, ioc) + ":STOP", 1)

    def restart_ioc(self, prefix, ioc):
        """Restarts the specified IOC.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC
        """
        print_and_log("Restarting IOC %s" % ioc)
        caput(self.generate_prefix(prefix, ioc) + ":RESTART", 1)

    def get_ioc_status(self, prefix, ioc):
        """Gets the status of the specified IOC.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC
        """
        ans = caget(self.generate_prefix(prefix, ioc) + ":STATUS", as_string=True)
        if ans is None:
            raise Exception("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        return ans.upper()

    def ioc_exists(self, prefix, ioc):
        """Checks an IOC exists.

        Args:
            prefix (string) : The prefix for the instrument
            ioc (string) : The name of the IOC

        Returns:
            (bool) : Whether the IOC exists
        """
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except:
            return False