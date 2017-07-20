# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
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
Module for dealing with configuration of the logging.
"""
import os
import re
from datetime import datetime

from ArchiverAccess.logging_period_providers import LoggingPeriodProviderConst, LoggingPeriodProviderPV
from server_common.utilities import print_and_log

DEFAULT_LOG_PATH = "C:\logs"
"""Default path where logs should be writen"""

DEFAULT_LOGGING_PERIOD_IN_S = 1
"""If no period is given for the logging then this is the default"""

TIME_DATE_COLUMN_HEADING = "Date/time"
"""Column heading for the date and time column"""

DEFAULT_COLUMN_SEPARATOR = "\t"
"""Default separator between columns in the table"""


class ConfigBuilder(object):
    """
    Configuration builder a way of creating a config step by step
    """

    def __init__(self, filename_template, base_path=DEFAULT_LOG_PATH, default_field="VAL"):
        """
        Constuctor
        Args:
            filename_template: the filename template to use; template that are replaced are `{xxx}` where xxx can be
                 start_time - for start date time of log
            base_path: the base path into which files should be placed
            default_field: the field appended to pvs without field; blank for don't add a field
        """

        self._default_field = default_field
        self._create_logs_from = datetime.now()
        self._filename_template = os.path.join(base_path, filename_template)
        self._header_lines = []
        self._columns = []
        self._trigger_pv = None
        self._logging_period_provider = None

    def header(self, header_line):
        """
        Add a templated line to the file header. Templates are similar to python formatters where the name of the
        argument is the pv name and the format can be specified after that using a | to separate it
        (in python it is a :). The value at the start of the log will be used.

        E.g. 'a line {TE:BLAH:SIMPLE:VALUE1|5.3f}' would return, if the value was 10, the line 'a line 10.000'

        Args:
            :param header_line: the header template line
            :return: self
        """
        self._header_lines.append(header_line)

        return self

    def build(self):
        """
        Build a configuration object from arguments
        Returns (Config): logging configuration

        """
        logging_period_provider = LoggingPeriodProviderConst(DEFAULT_LOGGING_PERIOD_IN_S)
        if self._logging_period_provider is not None:
            logging_period_provider = self._logging_period_provider
        return Config(self._filename_template, self._header_lines, self._columns, self._trigger_pv,
                      logging_period_provider, default_field=self._default_field)

    def table_column(self, heading, pv_template):
        """
        Add a table column
        Args:
            heading: heading for the table
            pv_template: pv template

        Returns: self

        """

        self._columns.append(
            {"header": heading,
             "pv_template": pv_template})

        return self

    def trigger_pv(self, pv_name):
        """
        PV from which to trigger the creation of a log file

        Args:
            pv_name: name of the pv to monitor

        Returns: self

        """
        self._trigger_pv = pv_name

        return self

    def logging_period_seconds(self, logging_period):
        """
        Constant logging period

        Args:
            logging_period: the logging period

        Returns: self

        """
        if self._logging_period_provider is not None:
            print_and_log("Logging period being redefined", severity="MINOR", src="ArchiverAccess")
        self._logging_period_provider = LoggingPeriodProviderConst(logging_period)

        return self

    def logging_period_pv(self, logging_period_pv):
        """
        Set a logging period depending on the value of a pv

        Args:
            logging_period_pv: pv to use for the logging period

        Returns: self

        """

        self._logging_period_provider = LoggingPeriodProviderPV(logging_period_pv, DEFAULT_LOGGING_PERIOD_IN_S)
        return self


class Config(object):
    """
    A complete valid configuration object for creating a single log file
    """

    def __init__(self, filename, header_lines, columns, trigger_pv, logging_period_provider, default_field="VAL"):
        """
        Constructor - this can be built using the builder

        Args:
            filename: filename template to use
            header_lines: header line templates
            columns: column definition
            trigger_pv: pv on which to trigger a log
            logging_period_provider(ArchiverAccess.logging_period_providers.LoggingPeriodProvider):
                an object which will supply the logging period
            default_field: field appended to PVs without a field
        """

        self._column_separator = DEFAULT_COLUMN_SEPARATOR

        if default_field is None or default_field == "":
            self._default_field = default_field
        else:
            self._default_field = "." + default_field

        self.trigger_pv = self._add_default_field(trigger_pv)
        self.filename = filename

        self._convert_header(header_lines)
        self.column_header_list = [TIME_DATE_COLUMN_HEADING]
        self._convert_column_headers(columns)
        self._convert_columns(columns)
        self.logging_period_provider = logging_period_provider

    def _convert_columns(self, columns):
        """
        Convert columns to table line and list of pvs contained
        Args:
            columns: list of column dictionaries

        Returns:

        """
        line_in_log_format = self._column_separator.join([str(x["pv_template"]) for x in columns])
        pv_names_in_columns = self._generate_pv_list([line_in_log_format])
        formatted_columns = self._convert_log_formats_to_python_formats(line_in_log_format, pv_names_in_columns)
        self.table_line = "{time}" + self._column_separator + formatted_columns

        self.pv_names_in_columns = self._add_all_default_fields(pv_names_in_columns)

    def _convert_column_headers(self, columns):
        """
        Convert column headers from header to a line that is at the top of the table

        Args:
            columns: columns to be converted

        Returns:

        """
        self.column_header_list.extend([x["header"] for x in columns])
        self.column_headers = self._column_separator.join(self.column_header_list)

    def _convert_header(self, header_lines):
        """
        Convert the header from lines containing templates to a line and pv names
        Args:
            header_lines: list of header lines

        Returns:

        """
        pv_names_in_header = self._generate_pv_list(header_lines)
        self.header = []
        for line in header_lines:
            final_line = self._convert_log_formats_to_python_formats(line, pv_names_in_header)
            self.header.append(final_line)

        self.pv_names_in_header = self._add_all_default_fields(pv_names_in_header)

    def _convert_log_formats_to_python_formats(self, line, pvs):
        """
        Convert a log format line to a python format line based on the list of pvs.

         The log format is {<pv name>!<converter>|<format>} which converts to {<index>!<converter>:<format>} where
          index is the index of <pv name> in the pvs list and converter and format are python string format converter
          and format (both are optional). For formatter mini-language see
           https://docs.python.org/2/library/string.html#format-specification-mini-language
        Args:
            line: line to convert
            pvs: a list of pvs to index

        Returns: converted line

        """
        final_line = line
        for index, pv in enumerate(pvs):
            # find the pv name and replace with argument index which it corresponds to
            final_line = re.sub('({)' + pv + '([|!]?[^}]*})', r'\g<1>' + str(index) + r'\g<2>', final_line)
            # replace the | with : in the format
            final_line = re.sub('({' + str(index) + '!?[^|}]*)\|([^}]*})', r'\1' + ':' + r'\2', final_line)
        return final_line

    def _generate_pv_list(self, lines):
        """
        Generate a pv list from a list of line.

        Args:
            lines: lines list of lines with log formats in

        Returns: list of unique pvs in lines

        """
        pvs = set()
        for line in lines:
            for match in re.finditer('{([^}|!]*)[|!]?[^}]*}', line):
                pv = match.group(1)
                pvs.add(pv)
        return list(pvs)

    def _add_default_field(self, pv_name):
        if pv_name is None or "." in pv_name:
            return pv_name
        return "{0}{1}".format(pv_name, self._default_field)

    def _add_all_default_fields(self, pv_names):
        """
        Add default field to pvs if they don't have fields.

        Args:
            pv_names: iterable pv names

        Returns: names with fields added

        """
        return [self._add_default_field(pv) for pv in pv_names]
