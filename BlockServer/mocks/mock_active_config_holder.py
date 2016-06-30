class MockActiveConfigHolder(object):
    def __init__(self):
        self.config_name = ""

    def get_config_name(self):
        return self.config_name

    def set_config_name(self, name):
        # This does not exist in the real thing
        self.config_name = name

