
class MockProcServWrapper(object):

    def __init__(self):
        self.ps_status = dict()
        self.ps_status["simple1"] = "SHUTDOWN"
        self.ps_status["simple2"] = "SHUTDOWN"
        self.ps_status["testioc"] = "SHUTDOWN"

    @staticmethod
    def generate_prefix(prefix, ioc):
        return "%sCS:PS:%s" % (prefix, ioc)

    def start_ioc(self, prefix, ioc):
        self.ps_status[ioc.lower()] = "RUNNING"

    def stop_ioc(self, prefix, ioc):
        """Stops the specified IOC"""
        self.ps_status[ioc.lower()] = "SHUTDOWN"

    def restart_ioc(self, prefix, ioc):
        self.ps_status[ioc.lower()] = "RUNNING"

    def get_ioc_status(self, prefix, ioc):
        if not ioc.lower() in self.ps_status.keys():
            raise Exception("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        else:
            return self.ps_status[ioc.lower()]

    def ioc_exists(self, prefix, ioc):
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except:
            return False
