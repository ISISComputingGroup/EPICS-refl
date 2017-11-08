# This file is part of the ISIS IBEX application.
# Copyright (C) 2017 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Module for creating a log file from a configuration and periodic data source.
"""

import os
from stat import S_IROTH, S_IRGRP, S_IREAD
from string import Formatter

from ArchiverAccess.periodic_data_generator import PeriodicDataGenerator
from server_common.utilities import print_and_log

FORMATTER_NOT_APPLIED_MESSAGE = " (formatter not applied: `{0}`)"
"""Message when a formatter can not be applied when writing a pv"""


class DataFileCreationError(Exception):
    """
    Exception that is thrown if the data file could not be created.
    """


class TemplateReplacer(object):
    """
    Code to replace templated values
    """

    def __init__(self, pv_values, start_time=None, time=None):
        """

        Args:
            start_time (datetime.datetime): time used to replace templated "start_time"
            time (datetime.datetime): time used to templated "time", e.g. start of logging ime for log filename
            pv_values: values of the pvs in order of keyword
        """

        self._pv_values = pv_values
        self._replacements = {}
        if start_time is not None:
            self._replacements["start_time"] = start_time.strftime("%Y-%m-%dT%H_%M_%S")
        if time is not None:
            time_as_string = time.strftime("%Y-%m-%dT%H:%M:%S")
            milliseconds = time.microsecond / 1000
            self._replacements["time"] = "%s.%03d" % (time_as_string, milliseconds)

    def replace(self, template):
        """
        Replace the values in the template with the pv values
        Args:
            template: template value to replace

        Returns: line with values in

        """
        try:
            return template.format(*self._pv_values, **self._replacements)
        except ValueError as ex:
            # incorrect formatter output without format
            template_no_format = ""
            for text, name, fomat_spec, conversion in Formatter().parse(template):
                template_no_format += "{text}{{{name}}}".format(text=text, name=name)
            if "Disconnected" not in self._pv_values and "Archive_Off" not in self._pv_values:
                template_no_format += FORMATTER_NOT_APPLIED_MESSAGE.format(ex)
            return template_no_format.format(*self._pv_values, **self._replacements)


def mkdir_for_file(filepath):
    """
    Make the directory tree for the file don't error if it already exists
    Args:
        filepath: path to create directory structure for

    Returns: nothing

    """
    abspath = os.path.abspath(os.path.dirname(filepath))
    if not os.path.isdir(abspath):
        os.makedirs(abspath)


def make_file_readonly_fn(filepath):
    """
    Make file readonly.
    Args:
        filepath: path to file

    Returns:

    """
    os.chmod(filepath, S_IREAD | S_IRGRP | S_IROTH)


class ArchiveDataFileCreator(object):
    """
    Archive data file creator creates the log file based on the configuration.
    """

    def __init__(self, config, archiver_data_source, file_access_class=file, mkdir_for_file_fn=mkdir_for_file,
                 make_file_readonly=make_file_readonly_fn):
        """
        Constructor
        Args:
            config(ArchiverAccess.configuration.Config):  configuration for the archive data file to create
            archiver_data_source: archiver data source
            file_access_class: file like object that can be written to
            mkdir_for_file_fn: function for creating the directories needed
            make_file_readonly: function to make a file readonly
        """
        self._config = config
        self._file_access_class = file_access_class
        self._archiver_data_source = archiver_data_source
        self._mkdir_for_file_fn = mkdir_for_file_fn
        self._make_file_readonly_fn = make_file_readonly
        self._filename = None
        self._first_line_written = False
        self._periodic_data_generator = None

    def write_complete_file(self, time_period):
        """
        Write the file to the file object.

        Args:
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period

        Raises DataFileCreationError: if there is a problem writing the log file

        """
        self.write_file_header(time_period.start_time)
        self.write_data_lines(time_period)
        self.finish_log_file()

    def finish_log_file(self):
        """
        Perform any post write tasks on the log file, e.g. make it read only.
        """
        try:
            self._make_file_readonly_fn(self._filename)
        except Exception as ex:
            raise DataFileCreationError("Failed to make log file {filename} readonly. "
                                        "Error is: '{exception}'"
                                        .format(exception=ex, filename=self._config.filename))

    def write_file_header(self, start_time, file_postfix=""):
        """
        Write the file header to a newly created file
        Args:
            start_time: start time of logging
            file_postfix: extra postfix to add the the file

        Raises DataFileCreationError: if there is a problem writing the log file

        """
        try:
            pv_names_in_header = self._config.pv_names_in_header
            pv_values = self._archiver_data_source.initial_values(pv_names_in_header, start_time)
            template_replacer = TemplateReplacer(pv_values, start_time=start_time)

            self._filename = template_replacer.replace(self._config.filename + file_postfix)
            print_and_log("Writing log file '{0}'".format(self._filename), src="ArchiverAccess")
            self._mkdir_for_file_fn(self._filename)
            with self._file_access_class(self._filename, mode="w") as f:
                for header_template in self._config.header:
                    header_line = template_replacer.replace(header_template)
                    f.write("{0}\n".format(header_line))

                f.write("{0}\n".format(self._config.column_headers))
            self._first_line_written = False
            self._periodic_data_generator = PeriodicDataGenerator(self._archiver_data_source)

        except Exception as ex:
            raise DataFileCreationError("Failed to write header in log file {filename} for start time {time}. "
                                        "Error is: '{exception}'"
                                        .format(time=start_time, exception=ex, filename=self._config.filename))

    def write_data_lines(self, time_period):
        """
        Append data lines to a file for the given time period. The first data line is appended only on the first call
        to this.
        Args:
            time_period: the time period to generate data lines for

        Raises DataFileCreationError: if there is a problem writing the log file

        """
        try:
            assert self._filename is not None, "Called write_data_lines before writing header."

            with self._file_access_class(self._filename, mode="a") as f:
                periodic_data = self._periodic_data_generator.get_generator(
                    self._config.pv_names_in_columns, time_period)
                self._ignore_first_line_if_already_written(periodic_data)

                for time, values in periodic_data:
                    table_template_replacer = TemplateReplacer(values, time=time)
                    table_line = table_template_replacer.replace(self._config.table_line)
                    f.write("{0}\n".format(table_line))

        except Exception as ex:
            raise DataFileCreationError("Failed to write lines in log file {filename} for time period {time_period}. "
                                        "Error is: '{exception}'"
                                        .format(time_period=time_period, exception=ex, filename=self._config.filename))

    def _ignore_first_line_if_already_written(self, periodic_data):
        """
        If this is the second call to this function then the first line will have been written as part of the output
         from the previous call so skip it.
        Args:
            periodic_data: periodic data

        """
        if self._first_line_written:
            periodic_data.next()
        else:
            self._first_line_written = True
