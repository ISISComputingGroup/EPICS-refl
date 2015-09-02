from BlockServer.mocks.mock_procserv_utils import MockProcServWrapper

IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')


class MockIocControl(object):

    def __init__(self, prefix):
        self._prefix = prefix
        self._proc = MockProcServWrapper()

    def start_ioc(self, ioc):
        self._proc.start_ioc(self._prefix, ioc)

    def restart_ioc(self, ioc, force):
        self._proc.restart_ioc(self._prefix, ioc)

    def stop_ioc(self, ioc):
        self._proc.stop_ioc(self._prefix, ioc)

    def get_ioc_status(self, ioc):
        return self._proc.get_ioc_status(self._prefix, ioc)

    def start_iocs(self, iocs):
        for ioc in iocs:
            self._proc.start_ioc(self._prefix, ioc)

    def restart_iocs(self, iocs):
        for ioc in iocs:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self.restart_ioc(ioc)

    def stop_iocs(self, iocs):
        for ioc in iocs:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self._proc.stop_ioc(self._prefix, ioc)

    def ioc_exists(self, ioc):
        try:
            self.get_ioc_status(self._prefix, ioc)
            return True
        except:
            return False

