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


class Block:
    """ Class holding Block details. Used for displaying in dataweb"""

    def __init__(self, name, status, value, alarm):
        """
        Standard constructor.

        Args:
            name: the name of the block
            status: the status of the block (e.g disconnected)
            value: the current block value
            alarm: the alarm status
        """
        self.name = name
        self.status = status
        self.value = value
        self.alarm = alarm
        
    def get_name(self):
        """ Returns the block name. """
        return self.name

    def set_name(self, name):
        """ Sets the block name. """
        self.name = name

    def get_status(self):
        """ Returns the block status. """
        return self.status

    def set_status(self, status):
        """ Sets the block status. """
        self.status = status

    def get_value(self):
        """ Returns the block value. """
        return self.value

    def set_value(self, value):
        """ Sets the block value. """
        self.value = value

    def get_alarm(self):
        """ Returns the block alarm state. """
        return self.alarm

    def set_alarm(self, alarm):
        """ Sets the block alarm state. """
        self.alarm = alarm

    def get_description(self):
        """ Returns the full description of this BoolStr object. """
        ans = dict()
        #ans["name"] = self.name
        ans["status"] = self.status
        ans["value"] = self.value
        ans["alarm"] = self.alarm
        return ans
