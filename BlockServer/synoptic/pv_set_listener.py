from abc import ABCMeta, abstractmethod


class PvSetListener(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def handle_pv_write(self, pv, data):
        pass