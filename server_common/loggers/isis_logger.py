"""
Access to external loggers at ISIS
"""

from __future__ import print_function, absolute_import, division, unicode_literals
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

import datetime
import socket
import contextlib
import traceback
import codecs

from concurrent.futures import ThreadPoolExecutor

from server_common.loggers.logger import Logger

# Server for the log servers
LOCALHOST = "127.0.0.1"

# TCP Port for the epics message logger
MESSAGE_LOG_LOGGER_PORT = 7004

# TCP for the put log logger
PUT_LOG_LOGGER_PORT = 7011


class IsisLogger(Logger):
    """
    Log messages into the IBEX server message log
    """

    executor = None

    def __init__(self, logger_port=MESSAGE_LOG_LOGGER_PORT, ioc_name="BLOCKSRV"):
        super(IsisLogger, self).__init__()
        self.ioc_log_host = LOCALHOST
        self.ioc_log_port = logger_port
        self._ioc_name = ioc_name
        self.start_thread_pool()

    @classmethod
    def start_thread_pool(cls):
        """
        Start the thread pool if not started
        """
        if cls.executor is None:
            cls.executor = ThreadPoolExecutor(max_workers=1)

    @classmethod
    def stop_thread_pool(cls):
        """
        Stop the thread pool; wait for pool to finish
        """
        if cls.executor is not None:
            cls.executor.shutdown(wait=True)
            cls.executor = None

    def write_to_log(self, message, severity="INFO", src=None):
        """Writes a message to the IOC log. It is preferable to use print_and_log for easier debugging.
        Args:
            message (string): message to write to the log
            severity (string, optional): Gives the severity of the message. Expected severities are MAJOR, MINOR and
                INFO. Default severity is INFO
            src (string, optional): Gives the source of the message. Defaults to loggers source.
        """
        if src is None:
            src = self._ioc_name
        msg_time = datetime.datetime.now()
        IsisLogger.executor.submit(
            self._queued_write_to_log, message, severity, src, self.ioc_log_host, self.ioc_log_port, msg_time)

    @staticmethod
    def _queued_write_to_log(message, severity, src, ioc_log_host, ioc_log_port, msg_time):
        if severity not in ['INFO', 'MINOR', 'MAJOR', 'FATAL']:
            print("write_to_ioc_log: invalid severity ", severity)
            return
        msg_time_str = msg_time.isoformat()
        if msg_time.utcoffset() is None:
            msg_time_str += "Z"

        xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        xml += "<message>"
        xml += "<clientName>%s</clientName>" % src
        xml += "<severity>%s</severity>" % severity
        xml += "<contents><![CDATA[%s]]></contents>" % message
        xml += "<type>ioclog</type>"
        xml += "<eventTime>%s</eventTime>" % msg_time_str
        xml += "</message>\n"

        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.connect((ioc_log_host, ioc_log_port))
                sock.sendall(codecs.encode(xml, "utf-8"))
            except Exception:
                traceback.print_exc()


class IsisPutLog:
    """
    ISIS Put Log records puts to a PV from sources external to the IOC/server. These are ultimately written to the put
    log if the ISIS IOC Log Sever is running.
    """

    def __init__(self, ioc_name):
        self.logger = IsisLogger(PUT_LOG_LOGGER_PORT, ioc_name)
        self._ioc_name = ioc_name

    def write_pv_put(self, pv_name, new_value, old_value):
        """
        Write a pv put to the put log
        Args:
            pv_name: name of the pv (should include instrument and server prefix)
            new_value: new value
            old_value:  original value
        """
        time_now = datetime.datetime.now()
        time_str = time_now.strftime("%d-%b-%y %H:%M:%S")
        message = "{} {} {} {} {} {}".format(time_str, LOCALHOST, self._ioc_name, pv_name, new_value, old_value)
        self.logger.write_to_log(message)
