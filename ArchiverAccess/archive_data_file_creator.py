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
from server_common.utilities import print_and_log, SEVERITY

FORMATTER_NOT_APPLIED_MESSAGE = " (formatter not applied: `{0}`)"
"""Message when a formatter can not be applied when writing a pv"""


class TemplateReplacer(object):
    """
    Code to replace templated values
    """

    def __init__(self, pv_values, time_period=None, time=None):
        """

        Args:
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period
            pv_values: values of the pvs in order of keyword
        """

        self._pv_values = pv_values
        self._replacements = {}
        if time_period is not None:
            self._replacements["start_time"] = time_period.start_time.strftime("%Y-%m-%dT%H_%M_%S")
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

    def write_complete_file(self, time_period):
        """
        Write the file to the file object.

        Args:
            time_period (ArchiverAccess.archive_time_period.ArchiveTimePeriod): time period

        Returns: True if log file as created and made readonly; False otherwise

        """

        if not self.write_file_header(time_period):
            return False

        if not self.write_data_lines(time_period):
            return False

        try:
            self._make_file_readonly_fn(self._filename)
            return True
        except Exception as ex:
            print_and_log("Failed to create log file {filename} for time period {time_period}. Error is: '{exception}'"
                          .format(time_period=time_period, exception=ex, filename=self._config.filename),
                          severity=SEVERITY.MAJOR, src="ArchiverAccess")
            return False

    def write_file_header(self, time_period):
        """
        Write the file header to a newly created file
        Args:
            time_period: time period to write the header for

        Returns: true if successful; False otherwise

        """
        try:
            pv_names_in_header = self._config.pv_names_in_header
            pv_values = self._archiver_data_source.initial_values(pv_names_in_header, time_period.start_time)
            template_replacer = TemplateReplacer(pv_values, time_period=time_period)

            self._filename = template_replacer.replace(self._config.filename)
            print_and_log("Writing log file '{0}'".format(self._filename), src="ArchiverAccess")
            self._mkdir_for_file_fn(self._filename)
            with self._file_access_class(self._filename, mode="w") as f:
                for header_template in self._config.header:
                    header_line = template_replacer.replace(header_template)
                    f.write("{0}\n".format(header_line))

                f.write("{0}\n".format(self._config.column_headers))

            return True
        except Exception as ex:
            print_and_log("Failed to create log file {filename} for time period {time_period}. Error is: '{exception}'"
                          .format(time_period=time_period, exception=ex, filename=self._config.filename),
                          severity=SEVERITY.MAJOR, src="ArchiverAccess")
            return False

    def write_data_lines(self, time_period):
        """
        Append data lines to a file for the given time period
        Args:
            time_period: the time period to generate data lines for

        Returns: True if success; False otherwise

        """
        try:

            assert self._filename is not None, "Called write_data_lines before writing header."

            periodic_data_generator = PeriodicDataGenerator(self._archiver_data_source)
            with self._file_access_class(self._filename, mode="a") as f:
                periodic_data = periodic_data_generator.get_generator(self._config.pv_names_in_columns, time_period)
                for time, values in periodic_data:
                    table_template_replacer = TemplateReplacer(values, time=time)
                    table_line = table_template_replacer.replace(self._config.table_line)
                    f.write("{0}\n".format(table_line))

            return True
        except Exception as ex:
            print_and_log("Failed to create log file {filename} for time period {time_period}. Error is: '{exception}'"
                          .format(time_period=time_period, exception=ex, filename=self._config.filename),
                          severity=SEVERITY.MAJOR, src="ArchiverAccess")
            return False
