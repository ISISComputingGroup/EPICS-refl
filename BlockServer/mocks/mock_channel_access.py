"""Channel Access Mocking Objects."""
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.  This program
# and the accompanying materials are made available under the terms of the
# Eclipse Public License v1.0 which accompanies this distribution.  EXCEPT AS
# EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM AND
# ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more
# details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

PVS = dict()
PV_TEST_DICT = None
PV_TEST_DICT_CALL_INDEX = None


class MockChannelAccess(object):
    """Mock Channel Access methods."""

    @staticmethod
    def caget(name, as_string=False):
        """Mock channel access get.

        Args:
            name (str): the PV to return a value for
            as_string (bool): this option is unimplemented
        """
        if PV_TEST_DICT is not None and name in PV_TEST_DICT:
            return MockChannelAccess._get_from_ca_env(name)
        if name in PVS:
            return PVS[name]
        return "Something that is not None"

    @staticmethod
    def _get_from_ca_env(name):
        call_index = PV_TEST_DICT_CALL_INDEX[name]
        PV_TEST_DICT_CALL_INDEX[name] += 1
        return PV_TEST_DICT[name][call_index]

    @staticmethod
    def caput(name, value, wait=False):
        """Mock channel access put.

        Args:
            name (str): the PV to set a value for
            value (any): the value to set the PV to
            wait (boo): this option is unimplemented
        """
        global PVS
        PVS[name] = value


class ChannelAccessEnv(object):
    """Channel access environment setup.

    Use this to create a channel access environment that can return different
    values depending on the number of times a PV is accessed. This will also
    track how many times a PV has been accessed.
    """

    def __init__(self, pv_values):
        """Create a new channel access environment.

        This will set up a number of PVs with a series of different values to
        return each time they are accessed.

        Args:
            pv_values (dict): dict of pv names and a list of values to return
                each time the PV is called
        """
        self._pv_values = pv_values
        self._old_values = None
        self._old_index = None

    def __enter__(self):
        """Create a global environment dict for channel access."""
        global PV_TEST_DICT, PV_TEST_DICT_CALL_INDEX
        self._old_values = PV_TEST_DICT
        self._old_index = PV_TEST_DICT_CALL_INDEX

        PV_TEST_DICT = self._pv_values
        PV_TEST_DICT_CALL_INDEX = {}
        for name in self._pv_values:
            PV_TEST_DICT_CALL_INDEX[name] = 0

        return self

    def __exit__(self, t, value, trace):
        """Tear down a global environment dict for channel access."""
        global PV_TEST_DICT, PV_TEST_DICT_CALL_INDEX
        PV_TEST_DICT = self._old_values
        PV_TEST_DICT_CALL_INDEX = self._old_index

    def get_call_count(self, name):
        """Get the number of times a PV was called."""
        global PV_TEST_DICT_CALL_INDEX
        return PV_TEST_DICT_CALL_INDEX[name]
