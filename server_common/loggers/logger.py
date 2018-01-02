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


class Logger(object):
    def __init__(self):
        pass

    def write_to_log(self, message, severity="INFO", src="BLOCKSVR"):
        """Writes a message to the log. Needs to be implemented in child class.
        Args:
            severity (string, optional): Gives the severity of the message. Expected serverities are MAJOR, MINOR
                                          and INFO (default).
            src (string, optional): Gives the source of the message. Default source is BLOCKSVR
        """
        pass
