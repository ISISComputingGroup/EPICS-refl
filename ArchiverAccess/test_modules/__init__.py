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
import os
import six
import unittest


def load_tests(loader, standard_tests, pattern):
    """
    This function is needed by the load_tests protocol described at
    https://docs.python.org/3/library/unittest.html#load-tests-protocol

    The tests in this module are only added under Python 2.
    """
    if six.PY2:
        standard_tests.addTests(loader.discover(os.path.dirname(__file__), pattern=pattern))
        return standard_tests
    else:
        return unittest.TestSuite()


