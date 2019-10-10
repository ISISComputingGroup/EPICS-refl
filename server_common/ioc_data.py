from __future__ import print_function, absolute_import, division, unicode_literals
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2017 Science & Technology Facilities Council.
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
from builtins import object
import six

"""
Module for reading data from the ioc database.
"""

from threading import RLock
from server_common.utilities import print_and_log


class IOCData(object):
    """
    A wrapper to connect to the IOC database and proc server.
    """

    def __init__(self, data_source, procserver, prefix):
        """Constructor

        Args:
            data_source (IocDataSource): The wrapper for the database that holds IOC information
            procserver (ProcServWrapper): An instance of ProcServWrapper, used to start and stop IOCs
            prefix (string): The pv prefix of the instrument the server is being run on
        """
        self._ioc_data_source = data_source
        self._procserve = procserver
        self._prefix = prefix
        self._running_iocs = list()
        self._running_iocs_lock = RLock()

    def get_iocs(self):
        """
        Gets a list of all the IOCs in the database and whether or not they are running.

        Returns:
            dict : IOCs and their running status
        """
        iocs = self._ioc_data_source.get_iocs_and_descriptions()
        for ioc in list(iocs.keys()):
            ioc = six.text_type(ioc)
            with self._running_iocs_lock:
                # Create a copy so we don't lock the list for longer than necessary (do we need to do this?)
                running = list(self._running_iocs)
            iocs[ioc]["running"] = ioc in running
        return iocs

    def get_active_iocs(self):
        """
        Gets a list of all the running IOCs.

        Returns:
            list : The names of running IOCs
        """
        return self._running_iocs

    def get_pars(self, category):
        """
        Gets parameters of a particular category from the IOC database.

        Returns:
            list : A list of the names of PVs associated with the parameter category
        """
        return self._ioc_data_source.get_pars(category)

    def get_beamline_pars(self):
        """
        Gets the beamline parameters from the IOC database.

        Returns:
            list : A list of the names of PVs associated with beamline parameters
        """
        return self.get_pars('BEAMLINEPAR')

    def get_sample_pars(self):
        """
        Gets the sample parameters from the IOC database.

        Returns:
            list : A list of the names of PVs associated with sample parameters
        """
        return self.get_pars('SAMPLEPAR')

    def get_user_pars(self):
        """
        Gets the user parameters from the IOC database.

        Returns:
            list : A list of the names of PVs associated with user parameters
        """
        return self.get_pars('USERPAR')

    def update_iocs_status(self):
        """
        Accesses the db to get a list of IOCs and checks to see if they are currently running.

        Returns:
            list : The names of running IOCs
        """
        with self._running_iocs_lock:
            self._running_iocs = []

            for ioc_name, is_running in self._ioc_data_source.get_iocs_and_running_status():
                # Check to see if running using CA and procserv
                try:
                    if self._procserve.get_ioc_status(self._prefix, ioc_name).upper() == "RUNNING":
                        self._running_iocs.append(ioc_name)
                        if is_running == 0:
                            # This should only get called if the IOC failed to tell the DB it started
                            self._ioc_data_source.update_ioc_is_running(ioc_name, 1)
                    else:
                        if is_running == 1:
                            self._ioc_data_source.update_ioc_is_running(ioc_name, 0)
                except Exception as err:
                    # Fail but continue - probably couldn't find procserv for the ioc
                    print_and_log("Issue with updating IOC status: %s" % err, "MAJOR", "DBSVR")

            return self._running_iocs

    def get_interesting_pvs(self, level="", ioc=None):
        """
        Queries the database for PVs based on their interest level and their IOC.

        Args:
            level (string, optional): The interest level to search for, either High, Medium or Facility. Default to
                                    all interest levels
            ioc (string, optional): The IOC to search. Default is all IOCs.

        Returns:
            list : A list of the PVs that match the search given by level and ioc
        """
        return self._ioc_data_source.get_interesting_pvs(level, ioc)

    def get_active_pvs(self):
        """
        Queries the database for interesting PVs from active IOCs.

        Returns:
            list : A list of the PVs in running IOCs

        """
        return self._ioc_data_source.get_active_pvs()
