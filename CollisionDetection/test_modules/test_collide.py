# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2018 Science & Technology Facilities Council.
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

from CollisionDetection.collide import collide

from unittest import TestCase

from hamcrest import *


class TestCollide(TestCase):
    def test_GIVEN_no_geometries_WHEN_collide_called_THEN_returns_empty_list(self):
        collisions = collide([], [])

        assert_that(collisions, is_([]))

    def test_GIVEN_one_geometries_WHEN_collide_called_THEN_returns_list_with_one_false(self):
        collisions = collide(["GEOMETRY_1"], [])

        assert_that(collisions, is_([False]))
