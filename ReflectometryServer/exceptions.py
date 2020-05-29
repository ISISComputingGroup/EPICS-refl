"""
Common Exceptions for the reflectometry IOC
"""

class BeamlineConfigurationInvalidException(Exception):
    """
    Exception for when a parameter is not initialized.
    """
    def __init__(self, err):
        self.message = str(err)

    def __str__(self):
        return self.message


class ParameterNotInitializedException(Exception):
    """
    Exception for when a parameter is not initialized.
    """
    def __init__(self, err):
        self.message = str(err)

    def __str__(self):
        return self.message


class NonExistentAxis(Exception):
    """
    Exception for when trying to access an axis which does not exist
    """
    def __init__(self, axis):
        self.axis = axis

    def __str__(self):
        return "NonExistentAxis: {} does not exist".format(self.axis)
