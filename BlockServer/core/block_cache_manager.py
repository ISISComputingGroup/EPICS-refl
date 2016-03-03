from server_common.channel_access import caget, caput
from server_common.utilities import print_and_log

BLOCKCACHE_PSC = "BLOCKCACHE"


class BlockCacheManager(object):
    """The BlockCache is a separate Python CAS which holds the current block values for use in cshow.
    This class allows the Block Server to control that CAS via ProcServCtrl.
    """
    def __init__(self, ioc_control):
        """Constructor.

        Args:
            ioc_control (IocControl): The object for restarting the IOC
        """
        self._ioc_control = ioc_control

    def restart(self):
        """ Restarts via ProcServCtrl.
        """
        try:
            if self._ioc_control.get_ioc_status(BLOCKCACHE_PSC) == "RUNNING":
                self._ioc_control.restart_ioc(BLOCKCACHE_PSC, force=True)
            else:
                self._ioc_control.start_ioc(BLOCKCACHE_PSC)
        except Exception as err:
            print_and_log("Problem with restarting the Block Cache: %s" % str(err), "MAJOR")