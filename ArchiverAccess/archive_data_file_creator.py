import os


class ArchiveDataFileCreator(object):
    """
    Archive data file creator creates the log file based on the configuration.
    """
    def __init__(self, config, file_access_class=file):
        """
        Constructor
        :param config: configuration for the archive data file to create
        :param file_access_class: file like object that can be written to
        """
        self._config = config
        self._file_access_class = file_access_class

    def write(self):
        """
        Write the file out
        :return:
        """
        with self._file_access_class(self._config.filename) as f:
            for header_line in self._config.header():
                f.write("{0}{1}".format(header_line, os.linesep))
