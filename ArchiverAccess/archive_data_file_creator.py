import os
from string import Formatter

# Message when a formatter can not be applied when writing a pv
FORMATTER_NOT_APPLIED_MESSAGE = " (formatter not applied)"


class PvValuesAtTime(object):
    """
    Generate PV Values at a given time as a dictionary
    """
    def __init__(self, archiver_data_source):
        """
        Constructor

        Args:
            archiver_data_source: archiver data source to read
        """
        self._archiver_data_source = archiver_data_source

    def get_values(self, time, pv_names):
        result = {}

        for pv_name, value in zip(pv_names, self._archiver_data_source.initial_values(pv_names, time)):
            result[pv_name] = value
        return result


class TemplateReplacer(object):
    """
    Code to replace templated values
    """

    def __init__(self, time_period, pv_values):
        """

        Args:
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period
            pv_values: dictionary of pv name and values
        """

        self._replacements = pv_values
        self._replacements["start_time"] = time_period.start_time.isoformat("T")

    def replace(self, template):
        """
        Replace the values in the template with the pv values
        Args:
            template: template value to replace

        Returns: line with values in

        """
        try:
            return template.format(**self._replacements)
        except ValueError:
            # incorrect formatter output without format
            template_no_format = ""
            for text, name, fomat_spec, conversion in Formatter().parse(template):
                template_no_format += "{text}{{{name}}}".format(text=text, name=name)
            template_no_format += FORMATTER_NOT_APPLIED_MESSAGE
            return template_no_format.format(**self._replacements)


class ArchiveDataFileCreator(object):
    """
    Archive data file creator creates the log file based on the configuration.
    """

    def __init__(self, config, time_period, archiver_data_source, file_access_class=file):
        """
        Constructor
        Args:
            config(ArchiverAccess.configuration.Config):  configuration for the archive data file to create
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period
            file_access_class: file like object that can be written to
        """
        self._config = config
        self._file_access_class = file_access_class
        self._time_period = time_period
        self._pv_values_at_time_provider = PvValuesAtTime(archiver_data_source)

    def write(self):
        """
        Write the file out
        :return:
        """

        #periodic_data_generator = PeriodicDataGenerator(start_time, period, point_count, archiver_data_source)

        pv_values = self._pv_values_at_time_provider.get_values(self._time_period.start_time, self._config.pv_names_in_header())
        template_replacer = TemplateReplacer(self._time_period, pv_values)

        filename = template_replacer.replace(self._config.filename)
        with self._file_access_class(filename) as f:
            for header_template in self._config.header():
                header_line = template_replacer.replace(header_template)
                f.write("{0}{1}".format(header_line, os.linesep))
