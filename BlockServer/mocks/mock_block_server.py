import json

class MockBlockServer(object):
    def __init__(self):
        self._comps = list()
        self._confs = list()

    def set_config_list(self, cl):
        self._config_list = cl

    def get_confs(self):
        return self._confs

    def update_config_monitors(self):
        self._confs = self._config_list.get_configs()

    def get_comps(self):
        return self._comps

    def update_comp_monitor(self):
        self._comps = self._config_list.get_subconfigs()

    def update_synoptic_monitor(self):
        pass
