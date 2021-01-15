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


class BeamlineConfigurationParkAutosaveInvalidException(Exception):
    """
    Raised when a  parks sequence autosave is not unparked or at the end of its sequence
    """

    def __init__(self, component_name, axis_name, sequence, max_sequence):
        self.component_name = component_name
        self.axis_name = axis_name
        self.sequence = sequence
        self.max_sequence = max_sequence

    def __str__(self):
        return f"The component {self.component_name} appears to be in the middle of a parking sequence, " \
               f"{self.sequence} of {self.max_sequence} steps. The error was found on axis {self.axis_name} but " \
               f"other axes may be involved. Please contact an instrument scientists and have them move the " \
               f"component back into the beam before anything else is moved. The positions can be found in the " \
               f"configuration file. The autosave position has now been overwritten so restarting the reflectometry " \
               f"server will not work."
