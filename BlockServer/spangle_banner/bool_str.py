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


class BoolStr:
    """ A class of banner item with display parameters for a string message based on different states of a bool PV """

    def __init__(self, name, pv):
        """
        Constructor.

        Args:
            name: The name of the banner item.
            pv: The associated PV which has to have "YES/NO" as possible values in order to be interpreted correctly
                by the GUI.
        """
        self.name = name
        self.pv = pv
        self.true_state = dict()
        self.false_state = dict()
        self.unknown_state = dict()

    def get_name(self):
        """ Returns the name of the banner item. """
        return self.name

    def get_pv(self):
        """ Returns the PV address associated to the banner item. """
        return self.pv

    def check_state_valid(self, state):
        """
        Checks that a given dictionary is valid with respect to the expected state format.

        Args:
            state (dictionary): The state definition whose validity is being checked.
        """
        if "colour" not in state or "message" not in state:
            raise Exception()

    def set_true_state(self, t_state):
        """ Sets display parameters for the True state. """
        self.check_state_valid(t_state)
        self.true_state = t_state

    def get_true_state(self):
        """ Returns display parameters for the True state. """
        return self.true_state

    def set_false_state(self, f_state):
        """ Sets display parameters for the False state. """
        self.check_state_valid(f_state)
        self.false_state = f_state

    def get_false_state(self):
        """ Returns display parameters for the False state. """
        return self.false_state

    def set_unknown_state(self, u_state):
        """ Sets display parameters for the Unknown state. """
        self.check_state_valid(u_state)
        self.unknown_state = u_state

    def get_unknown_state(self):
        """ Returns display parameters for the Unknown state. """
        return self.unknown_state

    def is_valid(self):
        """ Checks that this is a valid BoolStr object. """
        try:
            self.check_state_valid(self.true_state)
            self.check_state_valid(self.false_state)
            self.check_state_valid(self.unknown_state)
        except:
            return False

        return True

    def get_description(self):
        """ Returns the full description of this BoolStr object. """
        ans = dict()
        ans["type"] = "bool_str"
        ans["name"] = self.name
        ans["pv"] = self.pv
        ans["true_state"] = self.true_state
        ans["false_state"] = self.false_state
        ans["unknown_state"] = self.unknown_state
        return ans
