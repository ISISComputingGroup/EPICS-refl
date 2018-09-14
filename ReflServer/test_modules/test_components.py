import unittest

from math import tan, radians, sqrt
from hamcrest import *
from parameterized import parameterized

from ReflServer.components import Component, ReflectingComponent, TiltingJaws
from ReflServer.movement_strategy import LinearMovement
from ReflServer.gemoetry import Position, PositionAndAngle
from utils import position_and_angle, position


class TestComponent(unittest.TestCase):

    def test_GIVEN_jaw_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_is_same_as_beam_input(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.set_incoming_beam(beam_start)

        result = jaws.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(beam_start)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_0(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected_position = Position(y=0, z=jaws_z_position)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.set_incoming_beam(beam_start)

        result = jaws.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_60_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_at_tan_minus_60_times_10(self):
        jaws_z_position = 10.0
        beam_angle = 60.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        expected_position = Position(y=tan(radians(beam_angle)) * jaws_z_position, z=jaws_z_position)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.set_incoming_beam(beam_start)

        result = jaws.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_60_deg_and_z5_y30_WHEN_get_position_THEN_z_is_jaw_position_y_is_at_tan_minus_60_times_distance_between_input_beam_and_component_plus_original_beam_y(self):
        distance_between = 5.0
        start_z = 5.0
        start_y = 30
        beam_angle = 60.0
        jaws_z_position = distance_between + start_z
        beam_start = PositionAndAngle(y=start_y, z=start_z, angle=beam_angle)
        expected_position = Position(y=tan(radians(beam_angle)) * distance_between + start_y, z=jaws_z_position)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.set_incoming_beam(beam_start)

        result = jaws.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_tilting_jaw_input_beam_is_at_60_deg_WHEN_get_angle_THEN_angle_is_150_degrees(self):
        beam_angle = 60.0
        expected_angle = 60.0 + 90.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        jaws = TiltingJaws("tilting jaws", movement_strategy=LinearMovement(0, 20, 90))
        jaws.set_incoming_beam(beam_start)

        result = jaws.calculate_tilt_angle()

        assert_that(result, is_(expected_angle))


class TestActiveComponents(unittest.TestCase):

    def test_GIVEN_angled_mirror_is_disabled_WHEN_get_beam_out_THEN_outgoing_beam_is_incoming_beam(self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = beam_start

        mirror = ReflectingComponent("component", movement_strategy=LinearMovement(0, mirror_z_position, 90))
        mirror.angle = mirror_angle
        mirror.set_incoming_beam(beam_start)
        mirror.enabled = False

        result = mirror.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)))

    def test_GIVEN_mirror_with_input_beam_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_z_is_zmirror_y_is_ymirror_angle_is_input_angle_plus_device_angle(
            self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = PositionAndAngle(y=0, z=mirror_z_position, angle=2 * mirror_angle)

        mirror = ReflectingComponent("component", movement_strategy=LinearMovement(0, mirror_z_position, 90))
        mirror.angle = mirror_angle
        mirror.set_incoming_beam(beam_start)

        result = mirror.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)))

    @parameterized.expand([(-30, 60, 150),
                           (0, 0, 0),
                           (30, 30, 30),
                           (0, 90, 180),
                           (-40, -30, -20)])
    def test_GIVEN_mirror_with_input_beam_at_WHEN_get_beam_out_THEN_beam_output_correct(self, beam_angle,
                                                                                        mirror_angle,
                                                                                        outgoing_angle):
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        expected = PositionAndAngle(y=0, z=0, angle=outgoing_angle)

        mirror = ReflectingComponent("component", movement_strategy=LinearMovement(0, 0, 90))
        mirror.angle = mirror_angle
        mirror.set_incoming_beam(beam_start)

        result = mirror.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)),
                    "beam_angle: {}, mirror_angle: {}".format(beam_angle, mirror_angle))



            # def test_GIVEN_bench_at_radius_10_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_position_THEN_z_is_10_y_is_0(self):
    #     bench_center_of_rotation = Position(10, 0)
    #     bench_radius = 10
    #     beam_start = PositionAndAngle(z=0, y=0, angle=0)
    #     expected_position = Position(z=bench_center_of_rotation.z + bench_radius, y=0)
    #     bench = Component("component", movement_strategy=ArcMovement(bench_center_of_rotation, bench_radius))
    #     bench.set_incoming_beam(beam_start)
    #
    #     result = bench.calculate_beam_interception()
    #
    #     assert_that(result, is_(position(expected_position)))
    #
    # def test_GIVEN_bench_at_radius_10_input_beam_is_at_45_deg_and_z0_y0_WHEN_get_position_THEN_z_is_10_root2_y_is_10_root2(self):
    #     bench_center_of_rotation = Position(10, 0)
    #     bench_radius = 10
    #     beam_start = PositionAndAngle(z=0, y=0, angle=0)
    #     expected_position = Position(z=(bench_center_of_rotation.z + bench_radius) * sqrt(2), y=(bench_center_of_rotation.z + bench_radius) * sqrt(2))
    #     bench = Component("component", movement_strategy=ArcMovement(bench_center_of_rotation, bench_radius))
    #     bench.set_incoming_beam(beam_start)
    #
    #     result = bench.calculate_beam_interception()
    #
    #     assert_that(result, is_(position(expected_position)))


if __name__ == '__main__':
    unittest.main()
