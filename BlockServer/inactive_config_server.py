from config_holder import ConfigHolder
import json


class InactiveConfigServerManager(object):
    """Class to hold individual inactive configs"""

    def __init__(self, config_folder, macros, test_mode=False):
        self._config_holder = ConfigHolder(config_folder, macros)
        self._inactive_config_metas = dict()

        if test_mode:
            self._config_holder.set_testing_mode(True)

    def load_config(self, name, is_subconfig=False):
        config = self._config_holder.load_config(name, is_subconfig, False)
        self._config_holder.set_config(config, is_subconfig)

    def set_config_details(self, data):
        self._config_holder.set_config_details_from_json(json.loads(data))

    def get_config_name(self):
        return self._config_holder.get_config_name()

    def get_config_name_json(self):
        config = self._config_holder.get_config_name()
        return json.dumps(config).encode('ascii', 'replace')

    def save_config(self):
        name = self._config_holder.get_config_name()
        self._config_holder.save_config(name)

    def save_as_subconfig(self):
        conf = self._config_holder.get_config_name()
        self._config_holder.set_as_subconfig(True)
        self._config_holder.save_config(conf)

    def get_config_details_json(self):
        js = json.dumps(self._config_holder.get_config_details())
        return js.encode('ascii', 'replace')

    def get_config_meta(self):
        return self._config_holder.get_config_meta()