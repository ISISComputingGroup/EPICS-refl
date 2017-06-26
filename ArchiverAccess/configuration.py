class ConfigBuilder(object):
    """
    Configuration builder a way of creating a config step by step
    """

    def __init__(self, filename_template):
        """
        Constuctor
        :param filename_template: the filename template to use; template that are replaced are `{xxx}` where xxx can be
         first:time - for start date time of log
        """
        self.filename_template = filename_template
        self.header_lines = []

    def header(self, header_line):
        """
        Add a templated line to the file header. Templates are of the form {<how>:<PV NAME>}:
         where:
            <how> is how the values are place options are:
                 all - put all values in separated by commas
                 first-last - max and min values are shown separated by a dash(if they are the same a single value is shown)
            <PV NAME> is the pv to get values from

        :param header_line: the header template line
        :return: self
        """
        self.header_lines.append(header_line)

        return self

    def build(self):
        """
        Build a configuration object
        :return: configuration
        """
        return Config(self.filename_template, self.header_lines)


class Config(object):
    """
    A complete valid configuration object
    """

    def __init__(self, filename, header_lines):
        """
        Constructor - this should be built using the builder
        :param filename: filename template to use
        :param header_lines: header line templates
        """
        self.filename = filename
        self._header_lines = header_lines

    def header(self):
        """
        Get the header lines as a generator
        :return: header lines generator
        """
        for line in self._header_lines:
            yield line
