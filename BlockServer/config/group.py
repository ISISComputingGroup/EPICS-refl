class Group(object):
    """ Represents a group.

        Attributes:
            name (string): The name of the group
            blocks (dict): The blocks that are in the group
            component (string): The component the group belongs to
    """
    def __init__(self, name, component=None):
        """ Constructor.

        Args:
            name (string): The name for the group
            component (string): The component to which the group belongs
        """
        self.name = name
        self.blocks = []
        self.component = component

    def __str__(self):
        data = "Name: %s, COMPONENT: %s, Blocks: %s" % (self.name, self.component, self.blocks)
        return data

    def to_dict(self):
        """ Puts the group's details into a dictionary.

        Returns:
            dict : The group's details
        """
        return {'name': self.name, 'blocks': self.blocks, "component": self.component}
