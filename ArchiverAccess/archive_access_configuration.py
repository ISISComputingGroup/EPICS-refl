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
from ArchiverAccess.utilities import add_default_field
from server_common.utilities import print_and_log, SEVERITY

DEFAULT_LOG_PATH = os.path.join("C:\\", "logs")
"""Default path where logs should be writen"""

DEFAULT_LOGGING_PERIOD_IN_S = 1
"""If no period is given for the logging then this is the default"""

TIME_DATE_COLUMN_HEADING = "Date/time"
"""Column heading for the date and time column"""

DEFAULT_COLUMN_SEPARATOR = "\t"
"""Default separator between columns in the table"""


class ArchiveAccessConfigBuilder(object):
    """
    Configuration builder a way of creating an archive access configuration step by step using a fluid API.
    """

    def __init__(self, on_end_logging_filename_template=None, continuous_logging_filename_template=None,
                 base_path=DEFAULT_LOG_PATH, default_field="VAL"):
        """
        Constructor.
        Args:
            on_end_logging_filename_template: the filename template to use for the log on end file; None for don't
                create file template that are replaced are `{xxx}` where xxx can be start_time - for start date time of
                log
            continuous_logging_filename_template: the filename template to use for the log continuously file; When None
                don't create file. Curly brackets in teh template are replaced (as per python format) possible values
                are:
                    {start_time} - replace with start date time of log
            base_path: the base path into which files should be placed
            default_field: the field appended to pvs without a field e.g. VAL; blank for don't add a field
        """

        self._default_field = default_field
        self._create_logs_from = datetime.now()
        if on_end_logging_filename_template is None:
            self._on_end_logging_filename_template = None
        else:
            self._on_end_logging_filename_template = os.path.join(base_path, on_end_logging_filename_template)

        if continuous_logging_filename_template is None:
            self._continuous_logging_filename_template = None
        else:
            self._continuous_logging_filename_template = os.path.join(base_path, continuous_logging_filename_template)

        self._header_lines = []
        self._columns = []
        self._trigger_pv = None
        self._logging_period_provider = None

    def header(self, header_line):
        """
        Add a templated line to the file header. Templates are similar to python formaters where the name of the
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
        Returns (ArchiveAccessConfig): logging configuration

        """
        logging_period_provider = LoggingPeriodProviderConst(DEFAULT_LOGGING_PERIOD_IN_S)
        if self._logging_period_provider is not None:
            logging_period_provider = self._logging_period_provider
        return ArchiveAccessConfig(self._on_end_logging_filename_template,
                                   self._continuous_logging_filename_template,
                                   self._header_lines, self._columns, self._trigger_pv,
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
        if self._trigger_pv is not None:
            print_and_log("Trigger pv being redefined to {0} from {1}".format(pv_name, self._trigger_pv),
                          severity=SEVERITY.MAJOR, src="ArchiverAccess")

        self._trigger_pv = pv_name

        return self

    def logging_period_seconds(self, logging_period):
        """
        Constant logging period

        Args:
            logging_period: the logging period

        Returns: self

        """
        self._set_logging_period_provider(LoggingPeriodProviderConst(logging_period))

        return self

    def logging_period_pv(self, logging_period_pv):
        """
        Set a logging period depending on the value of a pv

        Args:
            logging_period_pv: pv to use for the logging period

        Returns: self

        """
        self._set_logging_period_provider(LoggingPeriodProviderPV(logging_period_pv, DEFAULT_LOGGING_PERIOD_IN_S))
        return self

    def _set_logging_period_provider(self, logging_period_provider):
        if self._logging_period_provider is not None:
            print_and_log("Logging period being redefined to {0} from {1}".format(
                logging_period_provider, self._logging_period_provider), severity=SEVERITY.MAJOR, src="ArchiverAccess")

        self._logging_period_provider = logging_period_provider


class ArchiveAccessConfig(object):
    """
    A complete valid configuration object for creating a single log file
    """

    def __init__(self, on_end_logging_filename_template, continuous_logging_filename_template, header_lines, columns,
                 trigger_pv, logging_period_provider, default_field="VAL"):
        """
        Constructor - this can be built using the builder

        Args:
            on_end_logging_filename_template: the filename template to use for the log on end file; None for don't
                create file template that are replaced are `{xxx}` where xxx can be start_time - for start date time of
                log
            continuous_logging_filename_template: the filename template to use for the log continuously file; When None
                don't create file. Curly brackets in teh template are replaced (as per python format) possible values
                are:
                    {start_time} - replace with start date time of log
            header_lines: header line templates
            columns: column definition
            trigger_pv: pv on which to trigger a log
            logging_period_provider(ArchiverAccess.logging_period_providers.LoggingPeriodProvider):
                an object which will supply the logging period
            default_field: field appended to PVs without a field
        """

        self._column_separator = DEFAULT_COLUMN_SEPARATOR

        self._default_field = default_field

        self.trigger_pv = add_default_field(trigger_pv, self._default_field)
        self.on_end_logging_filename_template = on_end_logging_filename_template
        self.continuous_logging_filename_template = continuous_logging_filename_template

        self._convert_header(header_lines)
        self.column_header_list = [TIME_DATE_COLUMN_HEADING]
        self._convert_column_headers(columns)
        self._convert_columns(columns)
        self.logging_period_provider = logging_period_provider
        self.logging_period_provider.set_default_field(self._default_field)

    def __rep__(self):
        rep = "Logging configuration (pvs as read from the archive)"
        rep += " - file (log on end): {0}".format(self.on_end_logging_filename_template)
        rep += " - file (continuous): {0}".format(self.continuous_logging_filename_template)
        rep += " - trigger pv: {0}".format(self.trigger_pv)
        rep += " - trigger pv: {0}".format(self.logging_period_provider)
        rep += " - file headers: {0}".format(self.header)
        rep += " - pvs in fileheader {0}".format(self.pv_names_in_header)
        rep += " - table headers: {0}".format(self.column_header_list)
        rep += " - table line: {0}".format(self.table_line)
        rep += " - pvs in table line {0}".format(self.pv_names_in_columns)
        return rep

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

    def _add_all_default_fields(self, pv_names):
        """
        Add default field to pvs if they don't have fields.

        Args:
            pv_names: iterable pv names

        Returns: names with fields added

        """
        return [add_default_field(pv, self._default_field) for pv in pv_names]
