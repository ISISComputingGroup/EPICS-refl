from config_holder import ConfigHolder
import json


class ConfigServerManager(object):
    """Class to hold individual inactive configs"""

    def __init__(self, config_folder, macros, test_mode=False):
        self._config_folder = config_folder
        self._macros = macros
        self._config_holder = ConfigHolder(self._config_folder, self._macros)

        if test_mode:
            self._config_holder.set_testing_mode(True)

    def clear_config(self):
        self._config_holder.clear_config()

    def set_config_details(self, json_data):
        self._config_holder.set_config_details_from_json(json.loads(json_data))

    def get_config_name(self):
        return self._config_holder.get_config_name()

    def get_config_name_json(self):
        config = self._config_holder.get_config_name()
        return json.dumps(config).encode('ascii', 'replace')

    def add_subconfigs(self, rawjson):
        data = json.loads(rawjson)
        for name in data:
            comp = self._config_holder.load_config(name, True)
            self._config_holder.add_subconfig(name, comp)

    def remove_subconfigs(self, rawjson):
        data = json.loads(rawjson)
        for name in data:
            self._config_holder.remove_subconfig(name)

    def save_config(self, rawjson=None):
        name = self._get_current_or_json_name(rawjson)
        self._save_config(name)

    def _save_config(self, name):
        self._config_holder.save_config(name)

    def save_as_subconfig(self, rawjson=None):
        name = self._get_current_or_json_name(rawjson)
        self._config_holder.set_as_subconfig(True)
        self._config_holder.save_config(name)

    def load_config(self, name, is_subconfig=False):
        self._load_config(name, is_subconfig)

    def _load_config(self, name, is_subconfig=False):
        config = self._config_holder.load_config(name, is_subconfig, False)
        self._config_holder.set_config(config, is_subconfig)

    def _get_current_or_json_name(self, rawjson):
        if rawjson is None:
            name = self._config_holder.get_config_name()
        else:
            # The config name comes as JSON
            name = json.loads(rawjson)
        return name

    def get_config_details(self):
        js = json.dumps(self._config_holder.get_config_details())
        return js.encode('ascii', 'replace')

    def get_config_meta(self):
        return self._config_holder.get_config_meta()

    def get_conf_subconfigs(self):
        return self._config_holder.get_component_names()

    def get_conf_subconfigs_json(self):
        """Gets a list of sub-configurations in the current config"""
        return json.dumps(self.get_conf_subconfigs()).encode('ascii', 'replace')

    def get_config_folder(self):
        return self._config_folder