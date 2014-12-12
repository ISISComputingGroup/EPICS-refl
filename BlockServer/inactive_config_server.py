__author__ = 'ffv81422'

from config_holder import ConfigHolder
import json

class InactiveConfigServer(object):
    def __init__(self, config_folder, macros):
        self._config_holder = ConfigHolder(config_folder, macros)

    def load_config(self, name, is_subconfig=False):
        config = self._config_holder.load_config(name, is_subconfig, False)
        self._config_holder.set_config(config, is_subconfig)

    def set_config_details(self, data):
        self._config_holder.set_config_details_from_json(json.loads(data))

    def get_config_name_json(self):
        config = self._config_holder.get_config_name()
        return json.dumps(config).encode('ascii', 'replace')

    def save_config(self, input):
        # The config name comes as JSON
        name = json.loads(input)
        self._config_holder.save_config(name)

    def save_as_subconfig(self, input):
        conf = json.loads(input)
        self._config_holder.set_as_subconfig(True)
        self._config_holder.save_config(conf)

    def get_config_details_json(self):
        js = json.dumps(self._config_holder.get_config_details())
        return js.encode('ascii', 'replace')