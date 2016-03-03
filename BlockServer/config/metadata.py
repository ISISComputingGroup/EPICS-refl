class MetaData(object):
    """Represents the metadata from a configuration/component.

    Attributes:
        name (string): The name of the configuration
        pv (string): The PV for the configuration
        description (string): The description
        synoptic (string): The default synoptic view for this configuration
        history (list): The save history of the configuration
    """
    def __init__(self, config_name, pv_name="", description="", synoptic=""):
        """ Constructor.

        Args:
            config_name (string): The name of the configuration
            pv (string): The PV for the configuration
            description (string): The description
            synoptic (string): The default synoptic view for this configuration
        """
        self.name = config_name
        self.pv = pv_name
        self.description = description
        self.synoptic = synoptic
        self.history = []

    def to_dict(self):
        """ Puts the metadata into a dictionary.

        Returns:
            dict : The metadata
        """
        return {'name': self.name, 'pv': self.pv, 'description': self.description, 'synoptic': self.synoptic,
                'history': self.history}