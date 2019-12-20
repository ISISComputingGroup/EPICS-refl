"""
Number of alternative parameters
"""


class ValueParameter:
    """
    A parameter of the beamline which is constant
    """
    def __init__(self, name, value, description=None):
        """
        Initialiser.
        Args:
            name: name of the value
            value: value for it to have (can be float or bool)
            description: description of what the value represents
        """
        self.name = name
        if description is None:
            self.description = name
        else:
            self.description = description
        self.value = value
