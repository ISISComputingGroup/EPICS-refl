class OptionsHolder(object):
    def __init__(self, options_folder, options_loader):
        self._config_options = options_loader.get_options(options_folder + '/config.xml')

    def get_config_options_string(self, iocname=None):
        if iocname is None:
            iocs = {}
            for k, v in self._config_options.iteritems():
                iocs[k] = v.to_dict()
            return iocs
        else:
            if iocname in self._config_options:
                return self._config_options[iocname].to_dict()
            else:
                return []