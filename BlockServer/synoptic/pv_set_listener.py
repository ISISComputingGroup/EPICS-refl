from abc import ABCMeta, abstractmethod


class PvSetListener(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def pv_exists(self, pv):
        pass

    @abstractmethod
    def handle_pv_write(self, pv, data):
        # Implementations of this method MUST run on a thread
        pass

    @abstractmethod
    def update_monitors(self):
        pass
