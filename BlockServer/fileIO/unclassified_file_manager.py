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

from server_common.utilities import print_and_log
from ConfigVersionControl.version_control_exceptions import UpdateFromVersionControlException


class UnclassifiedFileManager(object):
    """ Class for managing the PVs associated with devices"""

    def __init__(self, vc_manager):
        """ Constructor.

        Args:
            vc_manager (ConfigVersionControl): The manager to allow version control modifications
        """
        self._vc = vc_manager

    def recover_from_version_control(self):
        """ A method to revert the configurations directory back to the state held in version control."""
        try:
            self._vc.update()
        except UpdateFromVersionControlException as err:
            print_and_log("Unable to recover file from version control: %s" % err, "MINOR")

    def delete(self, name):
        pass

    def update(self):
        pass
