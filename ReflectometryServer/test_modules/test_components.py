import unittest

from math import tan, radians, sqrt
from hamcrest import *
from parameterized import parameterized

from ReflectometryServer.components import Component, ReflectingComponent, TiltingJaws
from ReflectometryServer.movement_strategy import LinearMovement
from ReflectometryServer.geometry import Position, PositionAndAngle
from utils import position_and_angle, position


class TestComponent(unittest.TestCase):

    def test_GIVEN_jaw_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_is_same_as_beam_input(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(beam_start)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_0(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected_position = Position(y=0, z=jaws_z_position)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_60_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_at_tan_minus_60_times_10(self):
        jaws_z_position = 10.0
        beam_angle = 60.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        expected_position = Position(y=tan(radians(beam_angle)) * jaws_z_position, z=jaws_z_position)
        jaws = Component("component", movement_strategy=LinearMovement(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_beam_interception()

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
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_tilting_jaw_input_beam_is_at_60_deg_WHEN_get_angle_THEN_angle_is_150_degrees(self):
        beam_angle = 60.0
        expected_angle = 60.0 + 90.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        jaws = TiltingJaws("tilting jaws", movement_strategy=LinearMovement(0, 20, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_tilt_angle()

        assert_that(result, is_(expected_angle))


class TestActiveComponents(unittest.TestCase):

    def test_GIVEN_angled_mirror_is_disabled_WHEN_get_beam_out_THEN_outgoing_beam_is_incoming_beam(self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = beam_start

        mirror = ReflectingComponent("component", movement_strategy=LinearMovement(0, mirror_z_position, 90))
        mirror.beam_path_set_point.angle = mirror_angle
        mirror.beam_path_set_point.set_incoming_beam(beam_start)
        mirror.beam_path_set_point.enabled = False

        result = mirror.beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)))

    def test_GIVEN_mirror_with_input_beam_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_z_is_zmirror_y_is_ymirror_angle_is_input_angle_plus_device_angle(
            self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = PositionAndAngle(y=0, z=mirror_z_position, angle=2 * mirror_angle)

        mirror = ReflectingComponent("component", movement_strategy=LinearMovement(0, mirror_z_position, 90))
        mirror.beam_path_set_point.angle = mirror_angle
        mirror.beam_path_set_point.set_incoming_beam(beam_start)

        result = mirror.beam_path_set_point.get_outgoing_beam()

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
        mirror.beam_path_set_point.angle = mirror_angle
        mirror.beam_path_set_point.set_incoming_beam(beam_start)

        result = mirror.beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)),
                    "beam_angle: {}, mirror_angle: {}".format(beam_angle, mirror_angle))



            # def test_GIVEN_bench_at_radius_10_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_position_THEN_z_is_10_y_is_0(self):
    #     bench_center_of_rotation = Position(10, 0)
    #     bench_radius = 10
    #     beam_start = PositionAndAngle(z=0, y=0, angle=0)
    #     expected_position = Position(z=bench_center_of_rotation.z + bench_radius, y=0)
    #     bench = Component("component", movement_strategy=ArcMovement(bench_center_of_rotation, bench_radius))
    #     bench.beam_path_set_point.set_incoming_beam(beam_start)
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
    #     bench.beam_path_set_point.set_incoming_beam(beam_start)
    #
    #     result = bench.calculate_beam_interception()
    #
    #     assert_that(result, is_(position(expected_position)))


class TestObservationOfComponentReadback(unittest.TestCase):
    """
    Tests for items observing changes in readbacks
    """

    def setUp(self):
        self._value = 0
        self._value2 = 0
        movement_strategy = LinearMovement(0, 0, 90)
        self.component = Component("test component", movement_strategy)

        self.component.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))

    def listen_for_value(self, source):
        self._value += 1

    def listen_for_value2(self, source):
        self._value2 += 1

    def test_GIVEN_listener_WHEN_readback_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_after_beam_path_update_listener(self.listen_for_value)
        self.component.beam_path_rbv.set_displacement(1)

        result = self.component.beam_path_rbv.get_displacement()

        assert_that(self._value, is_(1))
        assert_that(result, expected_value)

    def test_GIVEN_two_listeners_WHEN_readback_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_after_beam_path_update_listener(self.listen_for_value)
        self.component.beam_path_rbv.add_after_beam_path_update_listener(self.listen_for_value2)
        self.component.beam_path_rbv.set_displacement(1)

        result = self.component.beam_path_rbv.get_displacement()

        assert_that(self._value, is_(1))
        assert_that(self._value2, is_(1))
        assert_that(result, expected_value)

    def test_GIVEN_no_listener_WHEN_readback_changes_THEN_no_listeners_are_informed(self):
        self.component.beam_path_rbv.set_displacement(1)

        assert_that(self._value, is_(0))

    def test_GIVEN_listener_WHEN_beam_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_after_beam_path_update_listener(self.listen_for_value)
        beam_y = 1
        self.component.beam_path_rbv.set_displacement(expected_value + beam_y)

        self.component.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_y, 0, 0))
        result = self.component.beam_path_rbv.get_displacement()

        assert_that(self._value, is_(2))
        assert_that(result, expected_value)


if __name__ == '__main__':
    unittest.main()
