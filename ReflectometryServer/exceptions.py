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