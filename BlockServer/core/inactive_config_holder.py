import json

from BlockServer.core.config_holder import ConfigHolder


class InactiveConfigHolder(ConfigHolder):
    """Class to hold a individual inactive configuration or component"""

    def __init__(self, config_folder, macros, test_mode=False):
        super(InactiveConfigHolder, self).__init__(config_folder, macros)

        if test_mode:
            super(InactiveConfigHolder, self).set_testing_mode(True)

    # Could we override save_configuration?
    def save_inactive(self, name=None, as_comp=False):
        if name is None:
            name = super(InactiveConfigHolder, self).get_config_name()
        super(InactiveConfigHolder, self).save_configuration(name, as_comp)

    # Could we override load_configuration?
    def load_inactive(self, name, is_subconfig=False):
        config = super(InactiveConfigHolder, self).load_configuration(name, is_subconfig, False)
        super(InactiveConfigHolder, self).set_config(config, is_subconfig)
