class Group(object):
    """ Represents a group.

        Attributes:
            name (string): The name of the group
            blocks (dict): The blocks that are in the group
            subconfig (string): The component the group belongs to
    """
    def __init__(self, name, subconfig=None):
        """ Constructor.

        Args:
            name (string): The name for the group
            subconfig (string): The component to which the group belongs
        """
        self.name = name
        self.blocks = []
        self.subconfig = subconfig

    def __str__(self):
        data = "Name: %s, Subconfig: %s, Blocks: %s" % (self.name, self.subconfig, self.blocks)
        return data

    def to_dict(self):
        """ Puts the group's details into a dictionary.

        Returns:
            dict : The group's details
        """
        return {'name': self.name, 'blocks': self.blocks, "subconfig": self.subconfig}
