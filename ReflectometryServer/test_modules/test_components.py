import unittest

from math import tan, radians, isnan

from CaChannel._ca import AlarmSeverity
from hamcrest import *
from mock import Mock, patch, call
from parameterized import parameterized, parameterized_class

from ReflectometryServer import AxisParameter
from ReflectometryServer.beam_path_calc import BeamPathUpdate
from ReflectometryServer.axis import PhysicalMoveUpdate, DefineValueAsEvent
from ReflectometryServer.components import Component, ReflectingComponent, TiltingComponent, ThetaComponent
from ReflectometryServer.geometry import Position, PositionAndAngle, ChangeAxis
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate, IocDriver
from ReflectometryServer.test_modules.data_mother import create_mock_axis, get_standard_bench, ANGLE_OF_BENCH, \
    BENCH_MIN_ANGLE, BENCH_MAX_ANGLE
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

    def test_GIVEN_component_WHEN_set_relative_position_of_position_THEN_position_axis_has_changed_set_but_angle_does_not(self):

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


class TestActiveComponents(unittest.TestCase):

    def test_GIVEN_angled_mirror_is_not_in_beam_WHEN_get_beam_out_THEN_outgoing_beam_is_incoming_beam(self):
        mirror_z_position = 10
        mirror_angle = 15
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        expected = beam_start

        mirror = ReflectingComponent("component", setup=PositionAndAngle(0, mirror_z_position, 90))
        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(mirror_angle, None, None))
        mirror.beam_path_set_point.set_incoming_beam(beam_start)
        mirror.beam_path_set_point.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        mirror.beam_path_set_point.axis[ChangeAxis.POSITION].is_in_beam = False

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
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 10, 90))
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(isnan(result), is_(True), "Is not a number")

    def test_GIVEN_next_component_is_not_in_beam_WHEN_get_read_back_THEN_nan_returned(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))

        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = False
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(isnan(result), is_(True), "Is not a number")

    def test_GIVEN_next_component_is_in_beam_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(0.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam_and_at_45_degrees_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(45.0/2.0))

    def test_GIVEN_next_component_is_in_beam_and_at_90_degrees_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 5, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(90/2.0))

    def test_GIVEN_next_component_is_not_in_beam_and_next_component_but_one_is_in_beam_WHEN_get_read_back_THEN_half_angle_to_component_is_readback_and_theta_calc_set_of_incoming_beam_is_set(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        next_component = Component("comp1", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = False
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"

        next_but_one_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"

        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        theta.add_angle_to(next_component)
        theta.add_angle_to(next_but_one_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement
        theta_calc_set_of_incoming_beam_next_comp_but_one = next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(45.0/2.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(None), "This component does not define theta rbv")
        assert_that(theta_calc_set_of_incoming_beam_next_comp_but_one, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam_and_next_component_but_one_is_also_in_beam_WHEN_get_read_back_THEN_half_angle_to_first_component_is_readback_and_theta_cal_set_only_on_first_component(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)

        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))

        next_component = Component("comp1", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta.add_angle_to(next_component)

        next_but_one_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_but_one_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement = "Not None"
        theta.add_angle_to(next_but_one_component)

        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()
        theta_calc_set_of_incoming_beam_next_comp = next_component.beam_path_rbv.substitute_incoming_beam_for_displacement
        theta_calc_set_of_incoming_beam_next_comp_but_one = next_but_one_component.beam_path_rbv.substitute_incoming_beam_for_displacement

        assert_that(result, is_(45.0/2.0))
        assert_that(theta_calc_set_of_incoming_beam_next_comp, is_(position_and_angle(theta.beam_path_set_point.get_outgoing_beam())), "This component does not define theta rbv")
        assert_that(theta_calc_set_of_incoming_beam_next_comp_but_one, is_(None), "This component has defined theta rbv")

    def test_GIVEN_next_component_is_in_beam_WHEN_set_next_component_displacement_THEN_change_in_beam_path_triggered(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))

        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta.add_angle_to(next_component)

        theta.beam_path_rbv.set_incoming_beam(beam_start)
        listener = Mock()
        theta.beam_path_rbv.add_listener(BeamPathUpdate, listener)

        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1, None, None))

        listener.assert_called_once_with(BeamPathUpdate(theta.beam_path_rbv))

    def test_GIVEN_next_component_is_in_beam_WHEN_set_next_component_incoming_beam_THEN_change_in_beam_path_is_not_triggered(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(0, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        listener = Mock()
        theta.beam_path_rbv.add_listener(BeamPathUpdate, listener)

        next_component.beam_path_rbv.set_incoming_beam(PositionAndAngle(y=1, z=1, angle=1))

        listener.assert_not_called()

    def test_GIVEN_next_component_is_in_beam_and_at_45_degrees_and_not_on_axis_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=10, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(15, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(close_to(45.0/2.0, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_next_component_is_in_beam_and_at_45_degrees_and_incoming_angle_is_45_WHEN_get_read_back_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=10, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = TiltingComponent("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(45, None, None))
        theta.add_angle_of(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = theta.beam_path_rbv.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(close_to(45.0/2.0, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_next_component_is_in_beam_theta_is_set_to_0_and_component_is_at_45_degrees_WHEN_get_read_back_from_component_THEN_component_readback_is_relative_to_setpoint_beam_not_readback_beam_and_is_not_0_and_outgoing_beam_is_readback_outgoing_beam(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = Component("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        theta.add_angle_to(next_component)
        expected_position = 5
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(expected_position, None, None))

        theta.beam_path_set_point.set_incoming_beam(beam_start)
        theta.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(0)
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        next_component.beam_path_rbv.set_incoming_beam(theta.beam_path_rbv.get_outgoing_beam())

        result_position = next_component.beam_path_rbv.axis[ChangeAxis.POSITION].get_relative_to_beam()
        result_outgoing_beam = next_component.beam_path_rbv.get_outgoing_beam()

        assert_that(result_position, is_(expected_position))
        assert_that(result_outgoing_beam, is_(position_and_angle(theta.beam_path_rbv.get_outgoing_beam())))

    def test_GIVEN_next_component_is_in_beam_and_disabled_WHEN_theta_rbv_changed_THEN_beampath_on_rbv_is_updated(self):

        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = TiltingComponent("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_rbv.incoming_beam_can_change = False
        next_component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(0, None, None))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(5, None, None))
        theta.add_angle_to(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)

        result = next_component.beam_path_rbv.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(theta.beam_path_rbv.get_outgoing_beam())))

    def test_GIVEN_next_component_is_in_beam_and_at_45_degrees_and_incoming_angle_is_45_WHEN_get_init_sp_THEN_half_angle_to_component_is_readback(self):

        beam_start = PositionAndAngle(y=10, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = TiltingComponent("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        theta.add_angle_of(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        next_component.beam_path_set_point.axis[ChangeAxis.ANGLE].init_displacement_from_motor(45)

        result = theta.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(close_to(45.0/2.0, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_next_component_is_in_beam_and_at_47_degrees_with_an_autosaved_offset_of_2_and_incoming_angle_is_45_WHEN_get_init_sp_THEN_half_angle_to_component_minus_offset_is_readback(self):
        offset = 2
        beam_start = PositionAndAngle(y=10, z=0, angle=0)
        theta = ThetaComponent("theta", setup=PositionAndAngle(0, 5, 90))
        next_component = TiltingComponent("comp", setup=PositionAndAngle(0, 10, 90))
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        next_component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = True
        next_component.beam_path_set_point.axis[ChangeAxis.ANGLE].autosaved_value = offset
        theta.add_angle_of(next_component)
        theta.beam_path_rbv.set_incoming_beam(beam_start)
        next_component.beam_path_set_point.axis[ChangeAxis.ANGLE].init_displacement_from_motor(45 + offset)

        result = theta.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(result, is_(close_to(45.0/2.0, DEFAULT_TEST_TOLERANCE)))


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
        self.theta = ThetaComponent("theta", PositionAndAngle(0, z_theta, 90))
        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value = offset_comp
        self.theta.add_angle_to(self.component)
        self.theta.beam_path_set_point.set_incoming_beam(self.STRAIGHT_BEAM)
        expected = self.REFLECTION_ANGLE / 2.0

        self.component.beam_path_set_point.axis[ChangeAxis.POSITION].init_displacement_from_motor(z_theta + offset_comp)
        actual = self.theta.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam()

        assert_that(actual, is_(close_to(expected, DEFAULT_TEST_TOLERANCE)))


class TestComponentAlarms(unittest.TestCase):
    ALARM_SEVERITY = AlarmSeverity.Major
    ALARM_STATUS = AlarmStatus.Lolo
    ALARM = (ALARM_SEVERITY, ALARM_STATUS)
    UNDEFINED = (AlarmSeverity.Invalid, AlarmStatus.UDF)

    def setUp(self):
        self.component = ReflectingComponent("component", setup=PositionAndAngle(0, 2, 90))

    def test_WHEN_init_THEN_component_alarms_are_undefined(self):
        self.assertEqual(self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm, self.UNDEFINED)
        self.assertEqual(self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm, self.UNDEFINED)
        self.assertEqual(self.component.beam_path_set_point.axis[ChangeAxis.POSITION].alarm, self.UNDEFINED)
        self.assertEqual(self.component.beam_path_set_point.axis[ChangeAxis.ANGLE].alarm, self.UNDEFINED)

    def test_GIVEN_alarms_WHEN_updating_displacement_THEN_component_displacement_alarm_is_set(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)
        
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_displacement_THEN_component_angle_alarm_is_unchanged(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.UNDEFINED, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_angle_THEN_component_angle_alarm_is_set(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_alarms_WHEN_updating_angle_THEN_component_displacement_alarm_is_unchanged(self):
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.component.beam_path_rbv.axis[ChangeAxis.POSITION].alarm

        self.assertEqual(self.UNDEFINED, actual_alarm_info)

    def test_GIVEN_theta_angled_to_component_WHEN_updating_displacement_with_alarms_on_component_THEN_theta_angle_alarm_set(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))
        self.theta.add_angle_to(self.component)
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_theta_angled_of_component_WHEN_updating_displacement_with_alarms_on_component_THEN_theta_angle_alarm_set(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))
        self.theta.add_angle_of(self.component)
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.ALARM, actual_alarm_info)

    def test_GIVEN_theta_angled_to_component_WHEN_updating_angle_with_alarms_on_component_THEN_theta_angle_is_unchanged(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))
        self.theta.add_angle_to(self.component)
        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        self.assertEqual(self.UNDEFINED, actual_alarm_info)

    def test_GIVEN_theta_angled_to_two_components_one_not_in_beam_WHEN_updating_displacement_of_out_of_beam_coomponent_with_alarms_on_component_THEN_theta_angle_alarm_not_set(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))
        component2 = ReflectingComponent("component2", setup=PositionAndAngle(0, 2, 90))
        self.theta.add_angle_to(self.component)
        self.theta.add_angle_to(component2)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = False

        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        assert_that(actual_alarm_info, is_(self.UNDEFINED))

    def test_GIVEN_theta_angled_of_two_components_one_not_in_beam_WHEN_updating_displacement_of_out_of_beam_component_with_alarms_on_component_THEN_theta_angle_alarm_not_set(self):
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))
        component2 = ReflectingComponent("component2", setup=PositionAndAngle(0, 2, 90))
        self.theta.add_angle_of(self.component)
        self.theta.add_angle_of(component2)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = False

        update = CorrectedReadbackUpdate(0, self.ALARM_SEVERITY, self.ALARM_STATUS)

        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(update)
        actual_alarm_info = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].alarm

        assert_that(actual_alarm_info, is_(self.UNDEFINED))


class TestThetaChange(unittest.TestCase):

    def setUp(self):
        self.component = ReflectingComponent("comp", setup=PositionAndAngle(0, 0, 0))
        self.theta = ThetaComponent("theta", setup=PositionAndAngle(0, 1, 90))

    @parameterized.expand([(True,), (False,)])
    def test_GIVEN_component_pointed_at_by_theta_changes_WHEN_get_theta_change_THEN_theta_is_changing(self, is_changing):
        self.theta.add_angle_to(self.component)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing = is_changing

        result = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].is_changing

        assert_that(result, is_(is_changing), "Theta is changing")

    @parameterized.expand([(True,), (False,)])
    def test_GIVEN_2_components_pointed_at_by_theta_changes_when_first_out_of_beam_WHEN_get_theta_change_THEN_theta_is_changing_as_second_component(self, is_changing):
        self.theta.add_angle_to(self.component)
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing = not is_changing
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].has_out_of_beam_position = True
        self.component.beam_path_rbv.axis[ChangeAxis.POSITION].is_in_beam = False
        component2 = ReflectingComponent("cmp2", PositionAndAngle(0, 0, 0))
        self.theta.add_angle_to(component2)
        component2.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing = is_changing

        result = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].is_changing

        assert_that(result, is_(is_changing), "Theta is changing")

    @parameterized.expand([(True,), (False,)])
    def test_GIVEN_component_pointed_at_by_theta_changes_angle_of_WHEN_get_theta_change_THEN_theta_is_changing(self, is_changing):
        self.theta.add_angle_of(self.component)
        self.component.beam_path_rbv.axis[ChangeAxis.ANGLE].is_changing = is_changing

        result = self.theta.beam_path_rbv.axis[ChangeAxis.ANGLE].is_changing

        assert_that(result, is_(is_changing), "Theta is changing")

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
                                (ChangeAxis.PSI,),
                                (ChangeAxis.PHI,),
                                (ChangeAxis.HEIGHT,)])
class TestDirectAxisWithBenchComponent(unittest.TestCase):
    
    def test_GIVEN_axis_updated_WHEN_get_axis_THEN_updated_value_is_read(self):
        expected_result = 10
        bench = get_standard_bench()
        param = AxisParameter("PARAM", bench, self.axis)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, None, None))
        result = bench.beam_path_rbv.axis[self.axis].get_relative_to_beam()

        assert_that(result, is_(expected_result))

    def test_GIVEN_axis_updated_with_alarm_WHEN_get_see_saw_THEN_alarm_updated(self):
        expected_result = (AlarmSeverity.Major, AlarmStatus.Lolo)
        bench = get_standard_bench()
        param = AxisParameter("PARAM", bench, self.axis)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, *expected_result))
        result = bench.beam_path_rbv.axis[self.axis].alarm

        assert_that(result, is_(expected_result))

    def test_GIVEN_axis_updated_WHEN_THEN_physcal_move_triggered(self):
        self.physical_move = None

        def mylistener(pyhsical_move):
            self.physical_move = pyhsical_move

        expected_result = (AlarmSeverity.Major, AlarmStatus.Lolo)
        bench = get_standard_bench(with_z_position=0)
        param = AxisParameter("PARAM", bench, self.axis)
        bench.beam_path_rbv.axis[self.axis].add_listener(PhysicalMoveUpdate, mylistener)

        bench.beam_path_rbv.axis[self.axis].set_displacement(CorrectedReadbackUpdate(expected_result, *expected_result))
        result = self.physical_move.source

        assert_that(result, is_(bench.beam_path_rbv.axis[self.axis]))

    def test_GIVEN_set_axis_WHEN_get_axis_value_THEN_value_returned_and_axis_changed(self):
        expected_result = 10
        bench = get_standard_bench()
        param = AxisParameter("PARAM", bench, self.axis)

        param.sp = expected_result
        result = bench.beam_path_set_point.axis[self.axis].get_displacement()
        changed = bench.beam_path_set_point.axis[self.axis].is_changed

        assert_that(result, is_(expected_result))
        assert_that(changed, is_(True), "axis is changed")

    def test_GIVEN_axis_WHEN_define_position_THEN_position_define_event_occurs(self):
        self.define_event = None
        def mylistener(define_value):
            self.define_event = define_value
        expected_result = 10
        bench = get_standard_bench()
        bench.beam_path_rbv.axis[self.axis].add_listener(DefineValueAsEvent, mylistener)
        param = AxisParameter("PARAM", bench, self.axis)

        param.define_current_value_as.new_value = expected_result
        result_pos = self.define_event.new_position
        result_axis = self.define_event.change_axis

        assert_that(result_pos, is_(expected_result))
        assert_that(result_axis, is_(self.axis))

    def test_GIVEN_axis_parameter_WHEN_init_from_motor_on_component_THEN_parameter_sp_is_set(self):
        expected_result = 10
        bench = get_standard_bench()
        param = AxisParameter("PARAM", bench, self.axis)
        bench.beam_path_set_point.axis[self.axis].init_displacement_from_motor(expected_result)

        result = param.sp

        assert_that(result, is_(expected_result))


class TestBenchComponent(unittest.TestCase):

    def _setup_bench(self, initial_position):

        initial_angle, initial_height, initial_seesaw = initial_position
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        j1_axis = create_mock_axis("j1", 0, 1)
        j2_axis = create_mock_axis("j2", 0, 1)
        slide_axis = create_mock_axis("axis", 0, 1)
        j1_driver = IocDriver(bench, ChangeAxis.JACK_FRONT, j1_axis)
        j2_driver = IocDriver(bench, ChangeAxis.JACK_REAR, j2_axis)
        slide_driver = IocDriver(bench, ChangeAxis.SLIDE, slide_axis)
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        angle.sp = initial_angle
        seesaw.sp = initial_seesaw
        position.sp = initial_height
        j1_driver.perform_move(1, False)
        j2_driver.perform_move(1, False)
        slide_driver.perform_move(1, False)
        return position, angle, seesaw, j1_axis, j2_axis, slide_axis

    @parameterized.expand([
        (ChangeAxis.JACK_FRONT, 1, 1),
        (ChangeAxis.JACK_REAR, 1, 1),
        (ChangeAxis.JACK_FRONT, -4, -4),
        (ChangeAxis.JACK_REAR, 2, 2),
        (ChangeAxis.SLIDE, 1, 0)
    ])
    def test_GIVEN_set_height_axis_with_0_angle_WHEN_get_axis_value_THEN_j1_value_returned_and_axis_changed(self, axis, position, expected_result):
        bench = get_standard_bench(with_angle=0)
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, ChangeAxis.POSITION)

        param.sp = position
        result = bench.beam_path_set_point.axis[axis].get_displacement()
        changed = bench.beam_path_set_point.axis[axis].is_changed

        assert_that(result, is_(close_to(expected_result, 1e-6)))
        assert_that(changed, is_(True), "axis is changed")

    @parameterized.expand([
        (ChangeAxis.JACK_FRONT, 12.3,  202.2279727),  # expected values from spreadsheet + height
        (ChangeAxis.JACK_REAR, 12.3, 476.9454087),  # expected values from spreadsheet + height
        (ChangeAxis.JACK_FRONT, -0.1, -50.88767676),  # expected values from spreadsheet + height
        (ChangeAxis.JACK_REAR, 0.0, -111.3188069),  # expected values from spreadsheet + height
        (ChangeAxis.SLIDE, 3.3, 10.54157171), # expected values from spreadsheet + height
        (ChangeAxis.SLIDE, 0.1, -26.15894011),  # expected values from spreadsheet + height
        (ChangeAxis.SLIDE, BENCH_MIN_ANGLE, -27.44574943),  # expected values from spreadsheet + height at min angle
        (ChangeAxis.SLIDE, BENCH_MIN_ANGLE - 0.1, -27.44574943),  # expected values from spreadsheet + height at 0 deg because of cut off
        (ChangeAxis.SLIDE, BENCH_MAX_ANGLE, 24.79311549),  # expected values from spreadsheet + height at max angle
        (ChangeAxis.SLIDE, BENCH_MAX_ANGLE + 1.0, 24.79311549),  # expected values from spreadsheet + height at 4.8 deg because of cut off
    ])
    def test_GIVEN_set_height_axis_WHEN_get_axis_value_THEN_j1_value_returned_and_axis_changed(self, axis, angle, expected_result):
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)

        param.sp = angle
        result = bench.beam_path_set_point.axis[axis].get_displacement()
        changed = bench.beam_path_set_point.axis[axis].is_changed

        assert_that(result, is_(close_to(expected_result, 1E-6)))
        assert_that(changed, is_(True), "axis is changed")

    @parameterized.expand([
        (ChangeAxis.JACK_FRONT, 1, 1),
        (ChangeAxis.JACK_REAR, 1, -1),
        (ChangeAxis.JACK_FRONT, -4, -4),
        (ChangeAxis.JACK_REAR, -2, 2),
        (ChangeAxis.JACK_FRONT, 0, 0),
        (ChangeAxis.JACK_REAR, 0, 0)
    ])
    def test_GIVEN_set_seesaw_axis_with_0_angle_and_height_WHEN_get_axis_value_THEN_j1_value_returned_and_axis_changed(self, axis, see_saw, expected_result):
        bench = get_standard_bench(with_angle=0)
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        param = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)

        param.sp = see_saw
        result = bench.beam_path_set_point.axis[axis].get_displacement()
        changed = bench.beam_path_set_point.axis[axis].is_changed

        assert_that(result, is_(close_to(expected_result, 1e-6)))
        assert_that(changed, is_(True), "axis is changed")

    @parameterized.expand([
        ((ChangeAxis.POSITION, ChangeAxis.ANGLE, ChangeAxis.SEESAW), (), ( ), (ChangeAxis.JACK_FRONT,), True),
        ((), (ChangeAxis.POSITION, ChangeAxis.ANGLE, ChangeAxis.SEESAW), (ChangeAxis.JACK_FRONT,), (), False),
        ((), (ChangeAxis.POSITION, ChangeAxis.ANGLE, ChangeAxis.SEESAW), (ChangeAxis.JACK_REAR,), (), False),
        ((), (ChangeAxis.POSITION, ChangeAxis.ANGLE, ChangeAxis.SEESAW), (ChangeAxis.JACK_REAR,), (ChangeAxis.JACK_FRONT,), True),
        ((), (ChangeAxis.POSITION, ChangeAxis.ANGLE, ChangeAxis.SEESAW), (ChangeAxis.JACK_FRONT,), (ChangeAxis.SLIDE,), True),
    ])
    def test_GIVEN_changing_true_on_some_axis_WHEN_changing_set_on_an_axis_THEN_bench_angle_seesaw_and_height_on_changing_to_expected_answer(self, inital_setup_false, inital_setup_true, axes_to_set_false, axes_to_set_true, expected_result):
        bench = get_standard_bench(with_angle=0)
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        for axis in inital_setup_true:
            bench.beam_path_rbv.axis[axis].is_changing = True
        for axis in inital_setup_false:
            bench.beam_path_rbv.axis[axis].is_changing = False

        for axis in axes_to_set_false:
            bench.beam_path_rbv.axis[axis].is_changing = False

        for axis in axes_to_set_true:
            bench.beam_path_rbv.axis[axis].is_changing = True

        assert_that(bench.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing, is_(expected_result))
        assert_that(bench.beam_path_rbv.axis[ChangeAxis.ANGLE].is_changing, is_(expected_result))
        assert_that(bench.beam_path_rbv.axis[ChangeAxis.SEESAW].is_changing, is_(expected_result))

    @parameterized.expand([
        (1, 1, 1),
        (-4, -4, -4),
        (2, 2, 2)
    ])
    def test_GIVEN_set_jacks_with_height_with_0_angle_at_seesaw_setpoint_0_WHEN_get_control_axis_value_THEN_values_correct(self, jack_front_position, jack_rear_position, expected_position):
        bench = get_standard_bench(with_angle=0)
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        seesaw.sp = 0

        bench.beam_path_rbv.axis[ChangeAxis.JACK_FRONT].set_displacement(CorrectedReadbackUpdate(jack_front_position, AlarmSeverity.No, AlarmStatus.No))
        bench.beam_path_rbv.axis[ChangeAxis.JACK_REAR].set_displacement(CorrectedReadbackUpdate(jack_rear_position, AlarmSeverity.No, AlarmStatus.No))

        assert_that(position.rbv, is_(close_to(expected_position, 1e-6)))
        assert_that(angle.rbv, is_(close_to(0, 1e-6)))
        assert_that(seesaw.rbv, is_(close_to(0, 1e-6)))

    @parameterized.expand([
        (202.2279727, 476.9454087, 0, 12.3),
        (-46.6006546, -106.4529773, 0, 0.1),
        (-70.29056346, -160.1242782, 0, -1)
    ])
    def test_GIVEN_set_jacks_with_height_seesaw_setpoint_0_WHEN_get_control_axis_value_THEN_values_correct(self, jack_front_position, jack_rear_position, expected_position, expected_angle):
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        seesaw.sp = 0

        bench.beam_path_rbv.axis[ChangeAxis.JACK_FRONT].set_displacement(CorrectedReadbackUpdate(jack_front_position, AlarmSeverity.No, AlarmStatus.No))
        bench.beam_path_rbv.axis[ChangeAxis.JACK_REAR].set_displacement(CorrectedReadbackUpdate(jack_rear_position, AlarmSeverity.No, AlarmStatus.No))

        assert_that(position.rbv, is_(close_to(expected_position, 1e-6)))
        assert_that(angle.rbv, is_(close_to(expected_angle, 1e-6)))
        assert_that(seesaw.rbv, is_(close_to(0, 1e-6)))

    @parameterized.expand([
        (1, -1, ANGLE_OF_BENCH, 0, 1),
        (-1, 1, ANGLE_OF_BENCH, 0, -1),
        (-46.6006546 + 0.3, -106.4529773-0.3, 0.1, 0, 0.3),
        (-46.6006546 + 0.3 + 0.5, -106.4529773 - 0.3 + 0.5, 0.1, + 0.5, 0.3),
    ])
    def test_GIVEN_set_jacks_with_height_seesaw_setpoint_non_zero_WHEN_get_control_axis_value_THEN_values_correct(self, jack_front_position, jack_rear_position, angle_sp, expected_position, expected_seesaw):
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        angle.sp = angle_sp
        seesaw.sp = expected_seesaw

        bench.beam_path_rbv.axis[ChangeAxis.JACK_FRONT].set_displacement(CorrectedReadbackUpdate(jack_front_position, AlarmSeverity.No, AlarmStatus.No))
        bench.beam_path_rbv.axis[ChangeAxis.JACK_REAR].set_displacement(CorrectedReadbackUpdate(jack_rear_position, AlarmSeverity.No, AlarmStatus.No))

        assert_that(position.rbv, is_(close_to(expected_position, 1e-6)))
        assert_that(angle.rbv, is_(close_to(angle_sp, 1e-6)))
        assert_that(seesaw.rbv, is_(close_to(expected_seesaw, 1e-6)))

    NO_ALARM = (AlarmSeverity.No, AlarmStatus.No)
    MAJOR_ALARM = (AlarmSeverity.Major, AlarmStatus.HiHi)
    INVALID_ALARM = (AlarmSeverity.Invalid, AlarmStatus.Timeout)

    @parameterized.expand([
        (MAJOR_ALARM, NO_ALARM, NO_ALARM, MAJOR_ALARM),
        (NO_ALARM, MAJOR_ALARM, NO_ALARM, MAJOR_ALARM),
        (NO_ALARM, NO_ALARM, MAJOR_ALARM, MAJOR_ALARM),
        (INVALID_ALARM, NO_ALARM, MAJOR_ALARM, INVALID_ALARM)
    ])
    def test_GIVEN_set_alarms_on_jacks_and_slide_WHEN_get_control_axis_alarm_THEN_alarm_is_most_sever(self, front_alarm, rear_alarm, slide_alarm, expected_alarm):
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        angle.sp = 0
        seesaw.sp = 0

        bench.beam_path_rbv.axis[ChangeAxis.JACK_FRONT].set_displacement(CorrectedReadbackUpdate(0, *front_alarm))
        bench.beam_path_rbv.axis[ChangeAxis.JACK_REAR].set_displacement(CorrectedReadbackUpdate(0, *rear_alarm))
        bench.beam_path_rbv.axis[ChangeAxis.SLIDE].set_displacement(CorrectedReadbackUpdate(0, *slide_alarm))

        assert_that(position.alarm_severity, is_(expected_alarm[0]))
        assert_that(position.alarm_status, is_(expected_alarm[1]))

    @parameterized.expand([((ANGLE_OF_BENCH, 1, 0), 2, (2, 2, None)),
                           ((0, 1, 0), 0, (-48.74306278, -111.3188069, None)),
                           ((0.1, 1, 0), 0, (-46.6006546, -106.4529773, None)),
                           ((0, 1, 2), 0, (-48.74306278+2, -111.3188069-2, None)),])
    def test_GIVEN_bench_in_location_WHEN_define_position_THEN_new_height_defined(self, initial_position, define_height_as, expected_positions):
        expected_jack_front_height, expected_jack_rear_height, expected_slide_position = expected_positions
        position, angle, seesaw, j1_axis, j2_axis, slide_axis = self._setup_bench(initial_position)

        position.define_current_value_as.new_value = define_height_as

        assert_that(j1_axis.set_position_as_value, is_(close_to(expected_jack_front_height, 1e-6)))
        assert_that(j2_axis.set_position_as_value, is_(close_to(expected_jack_rear_height, 1e-6)))
        assert_that(slide_axis.set_position_as_value, is_(None))

    @parameterized.expand([((0.1, 0, 0), 0, (-48.74306278, -111.3188069, -27.44574943)),  # no height or seesaw set to 0
                           ((2, 0, 0), 0.1, (-46.6006546, -106.4529773, -26.15894011)),  # no height or seesaw set to non-zero
                           ((0, 0, 2), 0, (-48.74306278+2, -111.3188069-2, -27.44574943)),  # with seesaw
                           ((0, 1, 2), 0, (-48.74306278+1+2, -111.3188069+1-2, -27.44574943))])  # with height and seesaw
    def test_GIVEN_bench_in_location_WHEN_define_angle_THEN_new_height_defined(self, initial_position, define_height_as, expected_positions):
        expected_jack_front_height, expected_jack_rear_height, expected_slide_position = expected_positions
        position, angle, seesaw, j1_axis, j2_axis, slide_axis = self._setup_bench(initial_position)

        angle.define_current_value_as.new_value = define_height_as

        assert_that(j1_axis.set_position_as_value, is_(close_to(expected_jack_front_height, 1e-6)))
        assert_that(j2_axis.set_position_as_value, is_(close_to(expected_jack_rear_height, 1e-6)))
        assert_that(slide_axis.set_position_as_value, is_(close_to(expected_slide_position, 1e-6)))

    @parameterized.expand([((0, 0, 2), 0, (-48.74306278, -111.3188069, -27.44574943)),  # no height or angle set to 0
                           ((0, 0, 0), 3, (-48.74306278 + 3.0, -111.3188069 - 3.0, -27.44574943)),  # no height or angle set to non-zero
                           ((0.1, 0, 2), 0, (-46.6006546, -106.4529773, -26.15894011)),  # no height but angle set
                           ((0.1, 1, 2), 0, (-46.6006546 + 1, -106.4529773 + 1, -26.15894011))])  # height, and angle
    def test_GIVEN_bench_in_location_WHEN_define_seesaw_THEN_new_height_defined(self, initial_position, define_height_as, expected_positions):
        expected_jack_front_height, expected_jack_rear_height, expected_slide_position = expected_positions
        position, angle, seesaw, j1_axis, j2_axis, slide_axis = self._setup_bench(initial_position)

        seesaw.define_current_value_as.new_value = define_height_as

        assert_that(j1_axis.set_position_as_value, is_(close_to(expected_jack_front_height, 1e-6)))
        assert_that(j2_axis.set_position_as_value, is_(close_to(expected_jack_rear_height, 1e-6)))
        assert_that(slide_axis.set_position_as_value, is_(close_to(expected_slide_position, 1e-6)))

    @parameterized.expand([
        (0, 0, 0, ANGLE_OF_BENCH, 0, 0),  # seesaw zero
        (1, -1, 1, ANGLE_OF_BENCH, 0, 1),  # seesaw non-zero
        (0, 0, None, ANGLE_OF_BENCH, 0, 0),   # autosave not set
        (-46.6006546, -106.4529773, 0.0, 0.1, 0, 0.0),  # non-zero angle and zero seesaw
        (-46.6006546 + 0.3, -106.4529773-0.3, 0.3, 0.1, 0, 0.3),  # non-zero angle and seesaw
        (-46.6006546 + 0.3 + 0.5, -106.4529773 - 0.3 + 0.5, 0.3, 0.1, + 0.5, 0.3),   # non-zero angle and height and seesaw
    ])
    def test_GIVEN_jacks_init_with_height_seesaw_setpoint_set_WHEN_get_parameter_sp_THEN_values_correct(self, jack_front_position, jack_rear_position, seesaw_autosave, expected_angle, expected_position, expected_seesaw):
        bench = get_standard_bench()
        bench.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        position = AxisParameter("PARAM", bench, ChangeAxis.POSITION)
        with patch('ReflectometryServer.parameters.param_float_autosave') as bench_autosave:
            bench_autosave.read_parameter.return_value = seesaw_autosave
            seesaw = AxisParameter("PARAM", bench, ChangeAxis.SEESAW, autosave=True)
        angle = AxisParameter("PARAM", bench, ChangeAxis.ANGLE)
        j1_axis = create_mock_axis("j1", jack_front_position, 1)
        j2_axis = create_mock_axis("j2", jack_rear_position, 1)
        slide_axis = create_mock_axis("axis", 0.1, 1)
        j1_driver = IocDriver(bench, ChangeAxis.JACK_FRONT, j1_axis)
        j2_driver = IocDriver(bench, ChangeAxis.JACK_REAR, j2_axis)
        slide_driver = IocDriver(bench, ChangeAxis.SLIDE, slide_axis)

        j1_driver.initialise()
        j2_driver.initialise()
        slide_driver.initialise()

        assert_that(position.sp, is_(close_to(expected_position, 1e-6)))
        assert_that(angle.sp, is_(close_to(expected_angle, 1e-6)))
        assert_that(seesaw.sp, is_(close_to(expected_seesaw, 1e-6)))


if __name__ == '__main__':
    unittest.main()
