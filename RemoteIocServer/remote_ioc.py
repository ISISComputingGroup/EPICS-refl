from __future__ import print_function, unicode_literals, division, absolute_import


class RemoteIoc(object):
    def __init__(self, ioc_control, name):
        self.name = name
        self._ioc_control = ioc_control

    def start(self):
        self._ioc_control.start_ioc(self.name)

    def stop(self):
        self._ioc_control.stop_ioc(self.name, force=True)

    def restart(self):
        self._ioc_control.restart_ioc(self.name, force=True)
