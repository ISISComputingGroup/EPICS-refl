from BlockServer.config.configuration import Configuration
from BlockServer.core.inactive_config_holder import InactiveConfigHolder


def modify_active(name, macros, mock_file_manager, new_details, config_holder):
    config = Configuration(macros)
    config.meta.name = name
    inactive_config = InactiveConfigHolder(macros, mock_file_manager)
    inactive_config.set_config_details(new_details)
    inactive_config.save_inactive(name)

    config_holder.load_active(name)
