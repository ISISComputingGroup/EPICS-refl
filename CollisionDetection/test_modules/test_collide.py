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
from mock import MagicMock
from CollisionDetection.collide import collide
from unittest import TestCase


class MockGeometry(object):
    """
    Object to mock a geometry.
    """
    def __init__(self):
        self.geom = MagicMock()


def always_report_collisions(geom1, geom2):
    """
    Mocked collision function which always reports that any two geometries have collided.
    :param geom1: The first geometry to check
    :param geom2: The second geometry to check
    :return: True
    """
    return True


def never_report_collisions(geom1, geom2):
    """
    Mocked collision function which never reports that any two geometries have collided.
    :param geom1: The first geometry to check
    :param geom2: The second geometry to check
    :return: False
    """
    return False


class TestCollide(TestCase):
    def test_GIVEN_no_geometries_WHEN_collide_called_THEN_returns_empty_list(self):
        collisions = collide([], [])
        self.assertEqual(collisions, [])

    def test_GIVEN_one_geometries_WHEN_collide_called_THEN_returns_list_with_one_false(self):
        collisions = collide([MockGeometry()], [])
        self.assertEqual(collisions, [False])

    def test_GIVEN_two_identical_geometries_WHEN_collide_called_and_geometries_colliding_THEN_returns_list_with_one_true(self):
        collisions = collide([MockGeometry(), MockGeometry()], [], collision_func=always_report_collisions)
        self.assertTrue(len([x for x in collisions if x is True]) > 0)

    def test_GIVEN_two_identical_geometries_WHEN_collide_called_and_geometries_not_colliding_THEN_returns_list_with_no_collisions(self):
        collisions = collide([MockGeometry(), MockGeometry()], [], collision_func=never_report_collisions)
        self.assertTrue(len([x for x in collisions if x is True]) == 0)
