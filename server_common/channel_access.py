from __future__ import absolute_import, print_function, unicode_literals, division

"""
Make channel access not dependent on genie_python.
"""
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
from enum import Enum

from BlockServer.core.macros import MACROS
from server_common.utilities import print_and_log
from concurrent.futures import ThreadPoolExecutor

# Number of threads to serve caputs
NUMBER_OF_CAPUT_THREADS = 20

try:
    from genie_python.channel_access_exceptions import UnableToConnectToPVException, ReadAccessException
except ImportError:
    class UnableToConnectToPVException(IOError):
        """
        The system is unable to connect to a PV for some reason.
        """
        def __init__(self, pv_name, err):
            super(UnableToConnectToPVException, self).__init__("Unable to connect to PV {0}: {1}".format(pv_name, err))

    class ReadAccessException(IOError):
        """
        PV exists but its value is unavailable to read.
        """

        def __init__(self, pv_name):
            super(ReadAccessException, self).__init__("Read access denied for PV {}".format(pv_name))

try:
    # noinspection PyUnresolvedReferences
    from genie_python.genie_cachannel_wrapper import CaChannelWrapper, EXIST_TIMEOUT
except ImportError:
    print("ERROR: No genie_python on the system can not import CaChannelWrapper!")

try:
    from genie_python.genie_cachannel_wrapper import AlarmSeverity, AlarmCondition as AlarmStatus
except ImportError:
    class AlarmSeverity(Enum):
        """
        Enum for severity of alarm
        """
        No = 0
        Minor = 1
        Major = 2
        invalid = 3


    class AlarmStatus(Enum):
        """
        Enum for status of alarm
        """
        BadSub = 16
        Calc = 12
        Comm = 9
        Cos = 8
        Disable = 18
        High = 4
        HiHi = 3
        HwLimit = 11
        Link = 14
        Lolo = 5
        Low = 6
        No = 0
        Read = 1
        ReadAccess = 20
        Scam = 13
        Simm = 19
        Soft = 15
        State = 7
        Timeout = 10
        UDF = 17
        Write = 2
        WriteAccess = 21

def _create_caput_pool():
    """
    Returns: thread pool for the caputs
    """
    try:
        executor = ThreadPoolExecutor(max_workers=NUMBER_OF_CAPUT_THREADS, thread_name_prefix="ChannelAccess_Pool")
    except TypeError:
        executor = ThreadPoolExecutor(max_workers=NUMBER_OF_CAPUT_THREADS)
        print("WARNING: thread_name_prefix does not exist for ThreadPoolExecutor in this python, "
              "caput pool has generic name.")
    return executor


class ChannelAccess(object):
    # Create a thread poll so that threads are reused and so ca contexts that each thread gets are shared. This also
    # caps the number of ca library threads. 20 is chosen as being probably enough but limited.
    thread_pool = _create_caput_pool()

    @staticmethod
    def wait_for_tasks():
        """
        Wait for all requested tasks to complete, i.e. all caputs.

        It does this by shutting down the current threadpool waiting for all tasks to complete and then create a new
        pool.
        """
        ChannelAccess.thread_pool.shutdown()
        ChannelAccess.thread_pool = _create_caput_pool()

    @staticmethod
    def caget(name, as_string=False, timeout=None):
        """Uses CaChannelWrapper from genie_python to get a pv value. We import CaChannelWrapper when used as this means
        the tests can run without having genie_python installed

        Args:
            name (string): The name of the PV to be read
            as_string (bool, optional): Set to read a char array as a string, defaults to false
            timeout (float, None): timeout value to use; None for use default timeout

        Returns:
            obj : The value of the requested PV, None if no value was read
        """
        try:
            if timeout is None:
                return CaChannelWrapper.get_pv_value(name, as_string)
            else:
                return CaChannelWrapper.get_pv_value(name, as_string, timeout=timeout)

        except Exception as err:
            # Probably has timed out
            print_and_log(str(err))
            return None

    @staticmethod
    def caput(name, value, wait=False, set_pv_value=CaChannelWrapper.set_pv_value):
        """
        Uses CaChannelWrapper from genie_python to set a pv value. Waiting will put the call in a thread so the order
        is no longer guarenteed. Also if the call take time a queue will be formed of put tasks.

        We import CaChannelWrapper when used as this means the tests can run without having genie_python installed

        Args:
            name (string): The name of the PV to be set
            value (object): The data to send to the PV
            wait (bool, optional): Wait for the PV to set before returning
            set_pv_value: function to call to set a pv, used only in testing
        Returns:
            None: if wait is False
            Future: if wait if True
        """
        def _put_value():
            set_pv_value(name, value, wait)

        if wait:
            # If waiting then run in this thread.
            _put_value()
            return None
        else:
            # If not waiting, run in a different thread.
            # Even if not waiting genie_python sometimes takes a while to return from a set_pv_value call.
            return ChannelAccess.thread_pool.submit(_put_value)

    @staticmethod
    def caput_retry_on_fail(pv_name, value, retry_count=5):
        """
        Write to a pv and check the value is set, retry if not; raise if run out of retries
        Args:
            pv_name: pv name to write to
            value: value to write
            retry_count: number of retries

        Raises:
            IOError: if pv can not be set

        """
        current_value = None
        for _ in range(retry_count):
            ChannelAccess.caput(pv_name, value, wait=True)
            current_value = ChannelAccess.caget(pv_name)
            if current_value == value:
                break
        else:
            raise IOError("PV value can not be set, pv {}, was {} expected {}".format(pv_name, current_value, value))

    @staticmethod
    def pv_exists(name, timeout=None):
        """
        See if the PV exists.

        Args:
            name (string): The PV name.
            timeout(optional): How long to wait for the PV to "appear".

        Returns:
            True if exists, otherwise False.
        """
        if timeout is None:
            timeout = EXIST_TIMEOUT
        return CaChannelWrapper.pv_exists(name, timeout)

    @staticmethod
    def add_monitor(name, call_back_function):
        """
        Add a callback to a pv which responds on a monitor (i.e. value change). This currently only tested for
        numbers.
        Args:
            name: name of the pv
            call_back_function: the callback function, arguments are value,
                alarm severity (AlarmSeverity),
                alarm status (AlarmStatus)
        """
        CaChannelWrapper.add_monitor(name, call_back_function)

    @staticmethod
    def poll():
        """
        Flush the send buffer and execute any outstanding background activity for all connected pvs.
        NB Connected pv is one which is in the cache
        """
        CaChannelWrapper.poll()

    @staticmethod
    def clear_monitor(name):
        """
        Clears the monitor on a pv if it exists
        """
        try:
            CaChannelWrapper.get_chan(name).clear_channel()
        except UnableToConnectToPVException:
            pass


class ManagerModeRequiredException(Exception):
    """
    Exception to be thrown if manager mode was required, but not enabled, for an operation.
    """
    def __init__(self, *args, **kwargs):
        super(ManagerModeRequiredException, self).__init__(*args, **kwargs)


def verify_manager_mode(channel_access=ChannelAccess(), message="Operation must be performed in manager mode"):
    """
    Verifies that manager mode is active, throwing an error if it was not active.

    Args:
        channel_access (ChannelAccess, optional): the channel access class to use
        message (str): Message given to exception if manager mode was not enabled.

    Raises:
        ManagerModeRequiredException: if manager mode was not enabled or was unable to connect
    """
    try:
        is_manager = channel_access.caget("{}CS:MANAGER".format(MACROS["$(MYPVPREFIX)"])).lower() == "yes"
    except UnableToConnectToPVException as e:
        raise ManagerModeRequiredException("Manager mode is required, but the manager mode PV did not connect "
                                           "(caused by: {})".format(e))
    except ReadAccessException as e:
        raise ManagerModeRequiredException("Manager mode is required, but the manager mode PV could not be read "
                                           "(caused by: {})".format(e))
    except Exception as e:
        raise ManagerModeRequiredException("Manager mode is required, but an unknown exception occurred "
                                           "(caused by: {})".format(e))

    if not is_manager:
        raise ManagerModeRequiredException(message)
