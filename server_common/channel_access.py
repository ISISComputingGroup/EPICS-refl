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
import time
from utilities import print_and_log


class ChannelAccess(object):
    @staticmethod
    def caget(name, as_string=False):
        """Uses CaChannelWrapper from genie_python to get a pv value. We import CaChannelWrapper when used as this means
        the tests can run without having genie_python installed

        Args:
            name (string): The name of the PV to be read
            as_string (bool, optional): Set to read a char array as a string, defaults to false

        Returns:
            obj : The value of the requested PV, None if no value was read
        """

        from genie_python.genie_cachannel_wrapper import CaChannelWrapper
        try:
            return CaChannelWrapper.get_pv_value(name, as_string)
        except Exception as err:
            # Probably has timed out
            print err
            return None

    @staticmethod
    def caput(name, value, wait=False):
        """Uses CaChannelWrapper from genie_python to set a pv value. We import CaChannelWrapper when used as this means
        the tests can run without having genie_python installed

        Args:
            name (string): The name of the PV to be set
            value (object): The data to send to the PV
            wait (bool, optional): Wait for the PV t set before returning

        Raises:
            Exception : If the PV failed to set
        """
        try:
            start = time.time()
            from genie_python.genie_cachannel_wrapper import CaChannelWrapper
            CaChannelWrapper.set_pv_value(name, value, wait)
            finish = time.time()
            print_and_log("Finished setting PV, delta t = {})".format(finish - start))
        except Exception as err:
            print err
            raise err

