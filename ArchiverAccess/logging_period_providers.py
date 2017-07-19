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
Module for defining retrieving of the period for the logging
"""

import abc

from datetime import timedelta

from server_common.mysql_abstraction_layer import DatabaseError
from server_common.utilities import print_and_log

MINIMUM_LOGGING_PERIOD = 0.01
"""Smallest logging period allowed"""


class LoggingPeriodProvider(object):
    """
    Logging Period provider
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_logging_period(self, archive_data_source, time):
        """
        Get the logging period

        Args:
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource): data source
            time: time at which the logging period is needed

        Returns: logging period

        """
        raise NotImplementedError('users must define get_logging_period to use this base class')


class LoggingPeriodProviderConst(LoggingPeriodProvider):
    """
    Provide a logging period which is constant for all time
    """

    def __init__(self, logging_period):
        """
        Constructor
        Args:
            logging_period: the logging period in seconds to use
        """
        self._logging_period_const = logging_period

    def get_logging_period(self, archive_data_source, time):
        """
        Get the logging period

        Args:
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource): data source
            time: time at which the logging period is needed

        Returns: logging period

        """
        return timedelta(seconds=self._logging_period_const)


class LoggingPeriodProviderPV(LoggingPeriodProvider):
    """
    Get the logging period based on the value of a PV
    """

    def __init__(self, logging_period_pv, default_on_error):
        self._logging_period_pv = logging_period_pv
        self._period_on_error = timedelta(seconds=default_on_error)

    def get_logging_period(self, archive_data_source, time):
        """
        Get the logging period

        Args:
            archive_data_source(ArchiverAccess.archiver_data_source.ArchiverDataSource): data source
            time: time at which the logging period is needed

        Returns: logging period

        """
        logging_periods = ""

        try:
            logging_periods = archive_data_source.initial_values([self._logging_period_pv], time)
            if logging_periods[0] >= MINIMUM_LOGGING_PERIOD:
                return timedelta(seconds=logging_periods[0])
            else:
                print_and_log("Error logging period to small, from {0} got value '{1}'"
                              .format(self._logging_period_pv, logging_periods), src="ArchiverAccess")
                return self._period_on_error
        except DatabaseError:
            return self._period_on_error
        except (TypeError, ValueError, IndexError):
            print_and_log("Error when getting logging period from {0} got value '{1}'"
                          .format(self._logging_period_pv, logging_periods), src="ArchiverAccess")
            return self._period_on_error
