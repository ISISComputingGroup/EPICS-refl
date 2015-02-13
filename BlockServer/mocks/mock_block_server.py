import json

class MockBlockServer(object):
    def __init__(self):
        self._comps = "[]"
        self._confs = "[]"

    def set_config_list(self, cl):
        self._config_list = cl

    def get_confs(self):
        return json.loads(self._confs)

    def update_config_monitors(self):
        self._confs = self._config_list.get_configs_json()

    def get_comps(self):
        return json.loads(self._comps)

    def update_comp_monitor(self):
        self._comps = self._config_list.get_subconfigs_json()
