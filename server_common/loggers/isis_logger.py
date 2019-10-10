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

from builtins import object
import datetime
import socket
import contextlib
import traceback
import codecs


class IsisLogger(object):
    def __init__(self):
        super(IsisLogger, self).__init__()
        self.ioclog_host = "127.0.0.1"
        self.ioclog_port = 7004

    def write_to_log(self, message, severity="INFO", src="BLOCKSVR"):
        """Writes a message to the IOC log. It is preferable to use print_and_log for easier debugging.
        Args:
            severity (string, optional): Gives the severity of the message. Expected serverities are MAJOR, MINOR and INFO.
                                        Default severity is INFO
            src (string, optional): Gives the source of the message. Default source is BLOCKSVR
        """
        if severity not in ['INFO', 'MINOR', 'MAJOR', 'FATAL']:
            print("write_to_ioc_log: invalid severity ", severity)
            return
        msg_time = datetime.datetime.utcnow()
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
                sock.connect((self.ioclog_host, self.ioclog_port))
                sock.sendall(codecs.encode(xml, "utf-8"))
            except Exception:
                traceback.print_exc()
