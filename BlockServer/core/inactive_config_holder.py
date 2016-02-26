import json

from BlockServer.core.config_holder import ConfigHolder


class InactiveConfigHolder(ConfigHolder):
    """ Class to hold a individual inactive configuration or component.
    """
    def __init__(self, config_folder, macros, vc_manager):
        super(InactiveConfigHolder, self).__init__(config_folder, macros, vc_manager)

    # Could we override save_configuration?
    def save_inactive(self, name=None, as_comp=False):
        """Saves a configuration or component that is not currently in use.

        Args:
            name (string) : The name to save it under
            as_comp (bool) : Whether to save it as a component
        """
        if name is None:
            name = super(InactiveConfigHolder, self).get_config_name()
        # See if comp or config already exists
        # if it does then load it
        super(InactiveConfigHolder, self).save_configuration(name, as_comp)

    # Could we override load_configuration?
    def load_inactive(self, name, is_component=False):
        """Loads a configuration or component into memory for editing only.

        Args:
            name (string) : The name of the configuration to load
            is_component (bool) : Whether it is a component
        """
        config = super(InactiveConfigHolder, self).load_configuration(name, is_component, False)
        super(InactiveConfigHolder, self).set_config(config, is_component)
