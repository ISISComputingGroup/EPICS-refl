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

import json
from bool_str import BoolStr

class Banner:
    """ A class for holding and returning the state of the banner in the form of a list of items it contains."""

    def __init__(self, prefix):
        self.items = list()
        print prefix

        """ Temporary workaround for LARMOR until loading banner description from file is implemented."""
        if "LARMOR" in prefix:
            self.add_bumpstrip()

    def get_description(self):
        """ Returns the banner state as JSON. """
        return json.dumps(self.items)

    def add_item(self, item):
        """ Add an item to the banner.

        Args:
            item (bool_str): The item being added.
        """
        if item.is_valid():
            self.items.append(item.get_description())

    def add_bumpstrip(self):
        """ Temporary workaround for LARMOR until loading banner description from file is implemented."""
        bumpstrip = BoolStr("Bump Strip", "DAE:TITLE:DISPLAY")
        t_state = {"colour": "GREEN", "message": "not tripped"}
        f_state = {"colour": "RED", "message": "tripped"}
        u_state = {"colour": "RED", "message": "unknown"}
        bumpstrip.set_true_state(t_state)
        bumpstrip.set_false_state(f_state)
        bumpstrip.set_unknown_state(u_state)
        self.add_item(bumpstrip)
