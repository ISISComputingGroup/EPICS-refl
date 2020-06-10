import unittest

from math import tan, radians, isnan

from CaChannel._ca import AlarmSeverity
from hamcrest import *
from mock import Mock, patch, call
from parameterized import parameterized, parameterized_class

from ReflectometryServer import AxisParameter
from ReflectometryServer.beam_path_calc import BeamPathUpdate, DefineValueAsEvent, PhysicalMoveUpdate
from ReflectometryServer.components import Component, ReflectingComponent, TiltingComponent, ThetaComponent, \
    BenchComponent
from ReflectometryServer.geometry import Position, PositionAndAngle, ChangeAxis
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.test_modules.utils import position_and_angle, position, DEFAULT_TEST_TOLERANCE
from server_common.channel_access import AlarmStatus


class TestComponent(unittest.TestCase):

    def test_GIVEN_jaw_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_is_same_as_beam_input(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("component", setup=PositionAndAngle(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(beam_start)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_0_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_0(self):
        jaws_z_position = 10
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected_position = Position(y=0, z=jaws_z_position)
        jaws = Component("component", setup=PositionAndAngle(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_jaw_at_10_input_beam_is_at_60_deg_and_z0_y0_WHEN_get_position_THEN_z_is_jaw_position_y_is_at_tan_minus_60_times_10(self):
        jaws_z_position = 10.0
        beam_angle = 60.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        expected_position = Position(y=tan(radians(beam_angle)) * jaws_z_position, z=jaws_z_position)
        jaws = Component("component", setup=PositionAndAngle(0, jaws_z_position, 90))
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
        jaws = Component("component", setup=PositionAndAngle(0, jaws_z_position, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)

        result = jaws.beam_path_set_point.calculate_beam_interception()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_component_has_offset_WHEN_requesting_intercept_in_mantid_coordinates_THEN_offset_is_ignored_in_result(self):
        beam_angle = 45.0
        comp_z = 10.0
        expected_y = comp_z
        expected_position = Position(expected_y, comp_z)
        comp = Component("comp", PositionAndAngle(0, comp_z, 90))
        beam = PositionAndAngle(0, 0, beam_angle)
        comp.beam_path_set_point.set_incoming_beam(beam)

        comp.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(5)
        result = comp.beam_path_set_point.intercept_in_mantid_coordinates()

        assert_that(result, is_(position(expected_position)))

    def test_GIVEN_component_WHEN_set_relative_position_of_position_THEN_position_axis_has_changed_set(self):

        comp = Component("component", setup=PositionAndAngle(0, 0, 90))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(1)

        result = comp.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed

        assert_that(result, is_(True))


class TestTiltingJaws(unittest.TestCase):
    def test_GIVEN_tilting_jaw_input_beam_is_at_60_deg_WHEN_set_angular_displacement_THEN_beam_no_altered(self):
        beam_angle = 60.0
        beam_start = PositionAndAngle(y=0, z=0, angle=beam_angle)
        jaws = TiltingComponent("tilting jaws", setup=PositionAndAngle(0, 20, 90))
        jaws.beam_path_set_point.set_incoming_beam(beam_start)
        jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(123, None, None))

        result = jaws.beam_path_set_point.get_outgoing_beam()

        assert_that(result.angle, is_(beam_angle))

    def test_GIVEN_component_WHEN_set_relative_position_of_position_THEN_position_axis_has_changed_set_but_angle_doesnot(self):

        comp = TiltingComponent("component", setup=PositionAndAngle(0, 0, 90))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(1)

        result_pos = comp.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed
        result_angle = comp.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed

        assert_that(result_pos, is_(True))
        assert_that(result_angle, is_(False))

    def test_GIVEN_component_WHEN_set_relative_position_of_angle_THEN_angle_axis_has_changed_set_but_position_does_not(self):

        comp = TiltingComponent("component", setup=PositionAndAngle(0, 0, 90))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(1)

        result_pos = comp.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed
        result_angle = comp.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed

        assert_that(result_pos, is_(False))
        assert_that(result_angle, is_(True))

    def test_GIVEN_component_WHEN_set_in_beam_THEN_position_axis_has_changed_set_but_angle_doesnot(self):

        comp = TiltingComponent("component", setup=PositionAndAngle(0, 0, 90))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.set_in_beam(False)

        result_pos = comp.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed
        result_angle = comp.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed

        assert_that(result_pos, is_(True))
        assert_that(result_angle, is_(False))


class TestActiveComponents(unittest.TestCase):

    def test_GIVEN_angled_mirror_is_not_in_beam__WHEN_get_beam_out_THEN_outgoing_beam_is_incoming_beam(self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = beam_start

        mirror = ReflectingComponent("component", setup=PositionAndAngle(0, mirror_z_position, 90))
        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(mirror_angle, None, None))
        mirror.beam_path_set_point.set_incoming_beam(beam_start)
        mirror.beam_path_set_point.is_in_beam = False

        result = mirror.beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(expected)))

    def test_GIVEN_mirror_with_input_beam_at_0_deg_and_z0_y0_WHEN_get_beam_out_THEN_beam_output_z_is_zmirror_y_is_ymirror_angle_is_input_angle_plus_device_angle(
            self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = PositionAndAngle(y=0, z=mirror_z_position, angle=2 * mirror_angle)

        mirror = ReflectingComponent("component", setup=PositionAndAngle(0, mirror_z_position, 90))
        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(mirror_angle, None, None))
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

        mirror = ReflectingComponent("component", setup=PositionAndAngle(0, 0, 90))
        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(mirror_angle, None, None))
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
        movement_strategy = PositionAndAngle(0, 0, 90)
        self.component = Component("test component", movement_strategy)

        self.component.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))

    def listen_for_value(self, source):
        self._value += 1

    def listen_for_value2(self, source):
        self._value2 += 1

    def test_GIVEN_listener_WHEN_readback_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_listener(BeamPathUpdate, self.listen_for_value)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1, None, None))

        result = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement()

        assert_that(self._value, is_(1))
        assert_that(result, expected_value)

    def test_GIVEN_two_listeners_WHEN_readback_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_listener(BeamPathUpdate, self.listen_for_value)
        self.component.beam_path_rbv.add_listener(BeamPathUpdate, self.listen_for_value2)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1, None, None))

        result = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement()

        assert_that(self._value, is_(1))
        assert_that(self._value2, is_(1))
        assert_that(result, expected_value)

    def test_GIVEN_no_listener_WHEN_readback_changes_THEN_no_listeners_are_informed(self):
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1, None, None))

        assert_that(self._value, is_(0))

    def test_GIVEN_listener_WHEN_beam_changes_THEN_listener_is_informed(self):
        expected_value = 10
        self.component.beam_path_rbv.add_listener(BeamPathUpdate, self.listen_for_value)
        beam_y = 1
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(expected_value + beam_y, None, None))

        self.component.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_y, 0, 0))
        result = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement()

        assert_that(self._value, is_(2))
        assert_that(result, expected_value)


class TestThetaComponent(unittest.TestCase):

    def test_GIVEN_no_next_component_WHEN_get_read_back_THEN_nan_returned(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 10, 90), angle_to=[])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(isnan(result), is_(True), "Is not a number")

    def test_GIVEN_next_component_is_not_in_beam__WHEN_get_read_back_THEN_nan_returned(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = False
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(isnan(result), is_(True), "Is not a number")

    def test_GIVEN_next_component_is_in_beam_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(0.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam__and_at_45_degrees_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(45.0/2.0))

    def test_GIVEN_next_component_is_in_beam__and_at_90_degrees_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 5, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(90/2.0))

    def test_GIVEN_next_component_is_not_in_beam__and_next_component_but_one_is_in_beam__WHEN_get_read_back_THEN_half_angle_to_component_is_readback_and_theta_calc_set_of_incoming_beam_is_set(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp1", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = False
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"

        next_but_one_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_but_one_component.beam_path_rbv.is_in_beam = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"

        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component, next_but_one_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement
        theta_calc_set_of_incoming_beam_next_comp_but_one = next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(45.0/2.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(None), "This component does not define theta rbv")
        assert_that(theta_calc_set_of_incoming_beam_next_comp_but_one, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam__and_next_component_but_one_is_also_in_beam__WHEN_get_read_back_THEN_half_angle_to_first_component_is_readback_and_theta_cal_set_only_on_first_component(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp1", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))

        next_but_one_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_but_one_component.beam_path_rbv.is_in_beam = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"

        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component, next_but_one_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement
        theta_calc_set_of_incoming_beam_next_comp_but_one = next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(45.0/2.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component does not define theta rbv")
        assert_that(theta_calc_set_of_incoming_beam_next_comp_but_one, is_(None), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam__WHEN_set_next_component_displacement_THEN_change_in_beam_path_triggered(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        listener = Mock()
        theta.beam_path_rbv.add_listener(BeamPathUpdate, listener)

        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1, None, None))

        listener.assert_called_once_with(BeamPathUpdate(theta.beam_path_rbv))

    def test_GIVEN_next_component_is_in_beam__WHEN_set_next_component_incoming_beam_THEN_change_in_beam_path_is_not_triggered(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        listener = Mock()
        theta.beam_path_rbv.add_listener(BeamPathUpdate, listener)

        next_component.beam_path_rbv.set_incoming_beam(PositionAndAngle(y=1, z=1, angle=1))

        listener.assert_not_called()

    def test_GIVEN_next_component_is_in_beam_and_at_45_degrees_and_not_on_axis_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=10, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(15, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(close_to(45.0/2.0, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_next_component_is_in_beam__theta_is_set_to_0_and_component_is_at_45_degrees_WHEN_get_read_back_from_component_THEN_component_readback_is_relative_to_setpoint_beam_not_readback_beam_and_is_not_0_and_outgoing_beam_is_readback_outgoing_beam(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        expected_position = 5
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(expected_position, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_set_point.set_incoming_beam(beam_start)
        theta.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(0)
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        next_component.beam_path_rbv.set_incoming_beam(theta.beam_path_rbv.get_outgoing_beam())

        result_position = next_component.beam_path_rbv.axis[ChangeAxis.POSITION].get_relative_to_beam()
        result_outgoing_beam = next_component.beam_path_rbv.get_outgoing_beam()

        assert_that(result_position, is_(expected_position))
        assert_that(result_outgoing_beam, is_(position_and_angle(theta.beam_path_rbv.get_outgoing_beam())))

    def test_GIVEN_next_component_is_in_beam_and_diabled_WHEN_theta_rbv_changed_THEN_beampath_on_rbv_is_updated(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = TiltingComponent("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.is_in_beam = True
        next_component.beam_path_rbv.incoming_beam_can_change = False
        next_component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(0, None, None))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90), angle_to=[next_component])
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = next_component.beam_path_rbv.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(theta.beam_path_rbv.get_outgoing_beam())))


class TestComponentInitialisation(unittest.TestCase):

    def setUp(self):
        self.Z_COMPONENT = 10
        self.REFLECTION_ANGLE = 45
        self.STRAIGHT_BEAM = PositionAndAngle(y=0, z=0, angle=0)
        self.BOUNCED_BEAM = PositionAndAngle(y=0, z=0, angle=self.REFLECTION_ANGLE)
        self.EXPECTED_INTERCEPT = self.Z_COMPONENT
        self.EXPECTED_ANGLE = self.REFLECTION_ANGLE

        self.component = TiltingComponent("component", setup=PositionAndAngle(0, self.Z_COMPONENT, 90))
        self.component.beam_path_set_point.set_incoming_beam(PositionAndAngle(y=0, z=0, angle=0))

    # tests that changing beam on init does the right thing
    def test_GIVEN_component_has_autosaved_offset_WHEN_incoming_beam_changes_on_init_THEN_displacement_is_beam_intercept_plus_offset(self):
        autosaved_offset = 1
        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value = autosaved_offset
        expected = self.EXPECTED_INTERCEPT + autosaved_offset

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].get_displacement()

        assert_that(actual, is_(close_to(expected, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_component_has_autosaved_angle_WHEN_incoming_beam_changes_on_init_THEN_angle_is_beam_angle_plus_offset(self):
        autosaved_offset = 1
        self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].autosaved_value = autosaved_offset
        expected = self.EXPECTED_ANGLE + autosaved_offset

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement()

        assert_that(actual, is_(close_to(expected, DEFAULT_TEST_TOLERANCE)))


    def test_GIVEN_component_has_autosave_position_WHEN_incoming_beam_changes_on_init_THEN_pos_relative_to_beam_is_autosaved_offset(self):
        autosaved_offset = 1
        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value = autosaved_offset

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        self.assertEqual(autosaved_offset, actual)

    def test_GIVEN_component_has_autosave_angle_WHEN_incoming_beam_changes_on_init_THEN_angle_relative_to_beam_is_autosaved_offset(self):
        autosaved_offset = 1
        self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].autosaved_value = autosaved_offset

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        self.assertEqual(autosaved_offset, actual)

    def test_GIVEN_component_has_no_autosaved_offset_WHEN_incoming_beam_changes_on_init_THEN_displacement_is_unchanged(self):
        expected = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].get_displacement()

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].get_displacement()

        self.assertEqual(expected, actual)

    def test_GIVEN_component_has_no_autosaved_angle_WHEN_incoming_beam_changes_on_init_THEN_angle_is_unchanged(self):
        expected = self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement()

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement()

        self.assertEqual(expected, actual)

    def test_GIVEN_component_has_no_autosave_position_WHEN_incoming_beam_changes_on_init_THEN_pos_relative_to_beam_is_displacement_minus_beam_intercept(self):
        displacement = 5
        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(displacement, None, None))
        expected = displacement - self.EXPECTED_INTERCEPT

        self.component.beam_path_set_point.set_incoming_beam(self.BOUNCED_BEAM, on_init=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        assert_that(actual, is_(close_to(expected, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_theta_angled_to_autosaved_comp_WHEN_initialising_comp_THEN_theta_is_init_with_regards_to_beam_intercept(self):
        z_theta = self.Z_COMPONENT / 2
        offset_comp = 3
        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value = offset_comp
        self.theta = ThetaComponent("theta", PositionAndAngle(0, z_theta, 90), angle_to=[self.component])
        self.theta.beam_path_set_point.set_incoming_beam(self.STRAIGHT_BEAM)
        expected = self.REFLECTION_ANGLE / 2.0

        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].init_displacement_from_motor(z_theta + offset_comp)
        actual = self.theta.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(actual, is_(close_to(expected, DEFAULT_TEST_TOLERANCE)))


class TestComponentAlarms(unittest.TestCase):
    ALARM_SEVERITY = 1
    ALARM_STATUS = 2
    ALARM = (ALARM_SEVERITY, ALARM_STATUS)
    NO_ALARM = (None, None)

    def setUp(self):
        self.component = ReflectingComponent("component", setup=PositionAndAngle(0, 2, 90))

    def test_WHEN_init_THEN_component_alarms_are_none(self):
        self.assertEqual(self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm, self.NO_ALARM)
        self.assertEqual(self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm, self.NO_ALARM)
        self.assertEqual(self.component.beam_path_set_point.axis[ChangeAxis.POSITION].alarm, self.NO_ALARM)
        self.assertEqual(self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].alarm, self.NO_ALARM)

    def test_GIVEN_alarms_WHEN_updating_displacement_THEN_component_displacement_alarm_is_set(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)
        
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_displacement_THEN_component_angle_alarm_is_unchanged(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.NO_ALARM, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_angle_THEN_component_angle_alarm_is_set(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_angle_THEN_component_displacement_alarm_is_unchanged(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm

        self.assertEqual(self.NO_ALARM, actual_alarm_info)

    def test_GIVEN_theta_angled_to_component_WHEN_updating_displacement_with_alarms_on_component_THEN_theta_angle_alarm_set(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90), angle_to=[self.component])
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_theta_angled_to_component_WHEN_updating_angle_with_alarms_on_component_THEN_theta_angle_is_unchanged(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90), angle_to=[self.component])
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.NO_ALARM, actual_alarm_info)


class TestComponentDisablingAndAutosaveInit(unittest.TestCase):

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_disabled_THEN_incoming_beam_for_rbv_and_sp_are_saved(self, mock_auto_save):
        expected_incoming_beam_sp = PositionAndAngle(1, 2, 3)
        expected_incoming_beam_rbv = PositionAndAngle(1, 2, 3)
        expected_name = "comp"
        component = Component(expected_name, PositionAndAngle(0, 0, 0))
        component.beam_path_set_point.set_incoming_beam(expected_incoming_beam_sp)
        component.beam_path_rbv.set_incoming_beam(expected_incoming_beam_rbv)

        component.set_incoming_beam_can_change(False)

        mock_auto_save.write_parameter.assert_has_calls([call(expected_name + "_rbv", expected_incoming_beam_rbv),
                                                        call(expected_name + "_sp", expected_incoming_beam_sp)], any_order=True)

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_enabled_THEN_beamline_is_not_saved(self, mock_auto_save):
        component = Component("comp", PositionAndAngle(0, 0, 0))
        component.beam_path_set_point.set_incoming_beam(PositionAndAngle(1, 2, 3))

        component.set_incoming_beam_can_change(True)

        mock_auto_save.write_parameter.assert_not_called()

    def test_GIVEN_position_and_angle_WHEN_convert_for_autosave_and_back_THEN_is_same(self):
        expected_position_and_angle = PositionAndAngle(1, 2, 3)

        converted = PositionAndAngle.autosave_convert_for_write(expected_position_and_angle)
        result = PositionAndAngle.autosave_convert_for_read(converted)

        assert_that(result, is_(position_and_angle(expected_position_and_angle)))

    def test_GIVEN_position_and_angle_WHEN_convert_from_none_THEN_value_error(self):
        assert_that(calling(PositionAndAngle.autosave_convert_for_read).with_args(None),
                    raises(ValueError))

    def test_GIVEN_position_and_angle_WHEN_convert_from_nonsense_THEN_raises_value_error(self):

        assert_that(calling(PositionAndAngle.autosave_convert_for_read).with_args("blah"),
                    raises(ValueError))

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_init_disabled_with_valid_beam_THEN_incoming_beam_is_restored(self, mock_auto_save):
        expected_incoming_beam = PositionAndAngle(1, 2, 3)
        mock_auto_save.read_parameter.return_value = expected_incoming_beam
        component = Component("comp", PositionAndAngle(0, 0, 0))

        component.set_incoming_beam_can_change(False, on_init=True)

        assert_that(component.beam_path_set_point.get_outgoing_beam(), position_and_angle(expected_incoming_beam))

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_init_disabled_with_invalid_beam_THEN_incoming_beam_is_0_0_0(self, mock_auto_save):
        expected_incoming_beam = PositionAndAngle(0, 0, 0)
        mock_auto_save.read_parameter.return_value = None
        component = Component("comp", PositionAndAngle(0, 0, 0))

        component.set_incoming_beam_can_change(False, on_init=True)

        assert_that(component.beam_path_set_point.get_outgoing_beam(), position_and_angle(expected_incoming_beam))

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_init_enabled_with_valid_beam_THEN_incoming_beam_is_not_restored(self, mock_auto_save):
        expected_incoming_beam = PositionAndAngle(0, 0, 0)
        mock_auto_save.read_parameter.return_value = PositionAndAngle(12, 24, 63)
        component = Component("comp", PositionAndAngle(0, 0, 0))

        component.set_incoming_beam_can_change(True, on_init=True)

        assert_that(component.beam_path_set_point.get_outgoing_beam(), position_and_angle(expected_incoming_beam))

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_component_WHEN_disabled_and_incoming_beam_change_forced_THEN_incoming_beam_for_rbv_and_sp_are_saved(self, mock_auto_save):
        expected_incoming_beam_sp = PositionAndAngle(1, 2, 3)
        expected_incoming_beam_rbv = PositionAndAngle(1, 2, 3)
        expected_name = "comp"
        component = Component(expected_name, PositionAndAngle(0, 0, 0))
        component.beam_path_set_point.set_incoming_beam(PositionAndAngle(0,0,0))
        component.beam_path_rbv.set_incoming_beam(PositionAndAngle(0,0,0))
        component.set_incoming_beam_can_change(False)

        component.beam_path_set_point.set_incoming_beam(expected_incoming_beam_sp, force=True)
        component.beam_path_rbv.set_incoming_beam(expected_incoming_beam_rbv, force=True)

        mock_auto_save.write_parameter.assert_has_calls([call(expected_name + "_rbv", expected_incoming_beam_rbv),
                                                        call(expected_name + "_sp", expected_incoming_beam_sp)], any_order=True)


@parameterized_class(('axis'), [(ChangeAxis.SEESAW,),
                                (ChangeAxis.CHI,),
                                (ChangeAxis.TRANS, ),
                                (ChangeAxis.PSI,)])
class TestDirectAxisWithBenchComponent(unittest.TestCase):
    
    def test_GIVEN_seesaw_updated_WHEN_get_see_saw_THEN_updated_value_is_read(self):
        expected_result = 10
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, self.axis)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, None, None))
        result = bench.beam_path_rbv.axis[self.axis].get_relative_to_beam()

        assert_that(result, is_(expected_result))

    def test_GIVEN_seesaw_updated_with_alarm_WHEN_get_see_saw_THEN_alarm_updated(self):
        expected_result = (AlarmSeverity.Major, AlarmStatus.Lolo)
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, self.axis)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, *expected_result))
        result = bench.beam_path_rbv.axis[self.axis].alarm

        assert_that(result, is_(expected_result))

    def test_GIVEN_seesaw_updated_WHEN_THEN_physcal_move_triggered(self):
        self.physical_move = None

        def mylistener(pyhsical_move):
            self.physical_move = pyhsical_move

        expected_result = (AlarmSeverity.Major, AlarmStatus.Lolo)
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, self.axis)
        bench.beam_path_rbv.axis[self.axis].add_listener(PhysicalMoveUpdate, mylistener)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, *expected_result))
        result = self.physical_move.source

        assert_that(result, is_(bench.beam_path_rbv.axis[self.axis]))

    def test_GIVEN_set_seesaw_WHEN_get_axis_value_THEN_value_returned_and_axis_changed(self):
        expected_result = 10
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, self.axis)

        param.sp = expected_result
        result = bench.beam_path_set_point.axis[self.axis].get_displacement()
        changed = bench.beam_path_set_point.axis[self.axis].is_changed

        assert_that(result, is_(expected_result))
        assert_that(changed, is_(True), "axis is changed")

    def test_GIVEN_seesaw_WHEN_define_position_THEN_position_define_event_occurs(self):
        self.define_event = None
        def mylistener(define_value):
            self.define_event = define_value
        expected_result = 10
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        bench.beam_path_rbv.axis[self.axis].add_listener(DefineValueAsEvent, mylistener)
        param = AxisParameter("PARAM", bench, self.axis)

        param.define_current_value_as.new_value = expected_result
        result_pos = self.define_event.new_position
        result_axis = self.define_event.change_axis

        assert_that(result_pos, is_(expected_result))
        assert_that(result_axis, is_(self.axis))

    def test_GIVEN_seesaw_parameter_WHEN_init_from_motor_on_component_THEN_parameter_sp_is_set(self):
        expected_result = 10
        bench = BenchComponent("rear_bench", PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, self.axis)
        bench.beam_path_set_point.axis[self.axis].init_displacement_from_motor(expected_result)

        result = param.sp

        assert_that(result, is_(expected_result))


if __name__ == '__main__':
    unittest.main()
