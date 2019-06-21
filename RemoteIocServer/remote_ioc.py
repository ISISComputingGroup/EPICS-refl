from __future__ import print_function, unicode_literals, division


class RemoteIoc(object):
    def __init__(self, ioc_control, name):
        self.name = name
        self._ioc_control = ioc_control
        self.restart_required = False

    def start(self):
        self._ioc_control.start_ioc(self.name)

    def stop(self):
        self._ioc_control.stop_ioc(self.name, force=True)
        self.restart_required = False

    def restart(self):
        self._ioc_control.restart_ioc(self.name, force=True)
        self.restart_required = False
