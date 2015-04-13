class OptionsHolder(object):
    """Holds all the IOC options"""
    def __init__(self, options_folder, options_loader):
        """Constructor

        Args:
            options_folder (string) : The path of the directory holding the config.xml file
            options_loader (OptionsLoader) : An instance of OptionsLoader to load options from file
        """
        self._config_options = options_loader.get_options(options_folder + '/config.xml')

    def get_config_options(self):
        """Converts all stored IocOptions into dicts

        Returns:
            dict : IOCs and their associated options as a dictionary
        """
        iocs = {}
        for k, v in self._config_options.iteritems():
            iocs[k] = v.to_dict()
        return iocs