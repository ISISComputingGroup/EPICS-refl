import os
from BlockServer.config.configuration import Configuration


class MockConfigurationFileManager(object):

    def __init__(self):
        self.confs = dict()
        self.comps = dict()
        # Add the standard base config
        base = Configuration(None)
        base.set_name("_base")
        self.comps["_base"] = base

    def find_ci(self, root_path, name):
        """find a file with a case insensitive match"""
        res = ''
        for f in os.listdir(root_path):
            if f.lower() == name.lower():
                res = f
        return res

    def load_config(self, name, macros, is_component):
        if is_component:
            if name.lower() not in self.comps:
                raise IOError("Component could not be found: " + name)

            return self.comps[name.lower()]
        else:
            if name.lower() not in self.confs:
                raise IOError("Configuration could not be found: " + name)

            return self.confs[name.lower()]

    def save_config(self, configuration, is_component):
        # Just keep the config in memory
        if is_component:
            self.comps[configuration.get_name().lower()] = configuration
        else:
            self.confs[configuration.get_name().lower()] = configuration

    def component_exists(self, root_path, name):
        if name.lower() not in self.confs:
            raise Exception("Component does not exist")

    def copy_default(self, dest_path):
        pass
