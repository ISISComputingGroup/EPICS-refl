import os
import unittest

from math import tan, radians
from hamcrest import *
from mock import Mock, patch

from ReflectometryServer import *

import ReflectometryServer.file_io
from ReflectometryServer.test_modules.data_mother import DataMother, create_mock_axis, EmptyBeamlineParameter

from server_common.channel_access import AlarmSeverity, AlarmStatus
from utils import position_and_angle


class TestComponentBeamline(unittest.TestCase):

    def setup_beamline(self, initial_mirror_angle, mirror_position, beam_start):
        jaws = Component("jaws", setup=PositionAndAngle(0, 0, 90))
        mirror = ReflectingComponent("mirror", setup=PositionAndAngle(0, mirror_position, 90))
        mirror.beam_path_set_point.angle = initial_mirror_angle
        jaws3 = Component("jaws3", setup=PositionAndAngle(0, 20, 90))
        beamline = Beamline([jaws, mirror, jaws3], [], [], [], beam_start)
        return beamline, mirror

    def test_GIVEN_beam_line_contains_one_passive_component_WHEN_beam_set_THEN_component_has_beam_out_same_as_beam_in(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("jaws", setup=PositionAndAngle(0, 2, 90))
        beamline = Beamline([jaws], [], [], [], beam_start)

        result = beamline[0].beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(beam_start)))

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_beam_set_THEN_each_component_has_beam_out_which_is_effected_by_each_component_in_turn(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 45
        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)
        bounced_beam = PositionAndAngle(y=0, z=mirror_position, angle=initial_mirror_angle * 2)
        expected_beams = [beam_start, bounced_beam, bounced_beam]

        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component {}".format(index))


    def test_GIVEN_beam_line_contains_multiple_component_WHEN_angle_on_mirror_changed_THEN_beam_positions_are_all_recalculated(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 0

        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)

        mirror_final_angle = 45
        bounced_beam = PositionAndAngle(y=0, z=mirror_position, angle=mirror_final_angle * 2)
        expected_beams = [beam_start, bounced_beam, bounced_beam]

        mirror.beam_path_set_point.angle = mirror_final_angle
        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component index {}".format(index))

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_mirror_disabled_THEN_beam_positions_are_all_recalculated(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 45

        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)
        expected_beams = [beam_start, beam_start, beam_start]

        mirror.beam_path_set_point.is_in_beam = False
        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component index {}".format(index))


class TestComponentBeamlineReadbacks(unittest.TestCase):

    def test_GIVEN_components_in_beamline_WHEN_readback_changed_THEN_components_after_changed_component_updatereadbacks(self):
        comp1 = Component("comp1", PositionAndAngle(0, 1, 90))
        comp2 = Component("comp2", PositionAndAngle(0, 2, 90))
        beamline = Beamline([comp1, comp2], [], [], [DataMother.BEAMLINE_MODE_EMPTY])

        callback = Mock()
        comp2.beam_path_rbv.set_incoming_beam = callback
        comp1.beam_path_rbv.set_displacement(1.0, AlarmSeverity.No, AlarmStatus.No)

        assert_that(callback.called, is_(True))


class TestRealistic(unittest.TestCase):

    def test_GIVEN_beam_line_where_all_items_track_WHEN_set_theta_THEN_motors_move_to_be_on_the_beam(self):
        spacing = 2.0

        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)

        bl.parameter("s1").sp = 0
        bl.parameter("s3").sp = 0
        bl.parameter("det").sp = 0
        bl.parameter("det_angle").sp = 0

        theta_angle = 2
        bl.parameter("theta").sp = theta_angle

        assert_that(drives["s1_axis"].sp, is_(0))

        expected_s3_value = spacing * tan(radians(theta_angle * 2.0))
        assert_that(drives["s3_axis"].sp, is_(expected_s3_value))

        expected_det_value = 2 * spacing * tan(radians(theta_angle * 2.0))
        assert_that(drives["det_axis"].sp, is_(expected_det_value))

        assert_that(drives["det_angle_axis"].sp, is_(2*theta_angle))

    def test_GIVEN_beam_line_where_all_items_have_offset_WHEN_set_theta_THEN_motors_move_to_be_correct_distance_from_the_beam_theta_readback_is_correct_and_does_not_include_offset(self):
        spacing = 2.0

        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)

        s1_offset = 1.0
        bl.parameter("s1").sp = s1_offset
        s3_offset = 2.0
        bl.parameter("s3").sp = s3_offset
        det_offset = 3.0
        bl.parameter("det").sp = det_offset
        det_ang_offset = 4.0
        bl.parameter("det_angle").sp = det_ang_offset

        theta_angle = 2.0
        bl.parameter("theta").sp = theta_angle

        assert_that(drives["s1_axis"].sp, is_(s1_offset))
        assert_that(bl.parameter("s1").rbv, is_(s1_offset))

        expected_s3_value = spacing * tan(radians(theta_angle * 2.0)) + s3_offset
        assert_that(drives["s3_axis"].sp, is_(expected_s3_value))
        assert_that(bl.parameter("s3").rbv, is_(s3_offset))

        expected_det_value = 2 * spacing * tan(radians(theta_angle * 2.0)) + det_offset
        assert_that(drives["det_axis"].sp, is_(expected_det_value))
        assert_that(bl.parameter("det").rbv, is_(det_offset))

        assert_that(drives["det_angle_axis"].sp, is_(2*theta_angle + det_ang_offset))
        assert_that(bl.parameter("det_angle").rbv, close_to(det_ang_offset, 1e-6))

        assert_that(bl.parameter("theta").rbv, close_to(theta_angle, 1e-6))

    def test_GIVEN_beam_line_where_all_items_track_WHEN_set_theta_no_move_and_move_beamline_THEN_motors_move_to_be_on_the_beam(self):
        spacing = 2.0

        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)

        bl.parameter("s1").sp = 0
        bl.parameter("s3").sp = 0
        bl.parameter("det").sp = 0
        bl.parameter("det_angle").sp = 0

        theta_angle = 2
        bl.parameter("theta").sp_no_move = theta_angle
        bl.move = 1

        assert_that(drives["s1_axis"].sp, is_(0))

        expected_s3_value = spacing * tan(radians(theta_angle * 2.0))
        assert_that(drives["s3_axis"].sp, is_(expected_s3_value))

        expected_det_value = 2 * spacing * tan(radians(theta_angle * 2.0))
        assert_that(drives["det_axis"].sp, is_(expected_det_value))

        assert_that(drives["det_angle_axis"].sp, is_(2*theta_angle))

    def test_GIVEN_beam_line_which_is_in_disabled_mode_WHEN_set_theta_THEN_nothing_else_moves(self):
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)
        bl.parameter("s1").sp = 0
        bl.parameter("s3").sp = 0
        bl.parameter("det").sp = 0
        bl.parameter("det_angle").sp = 0
        bl.active_mode = "DISABLED"

        theta_angle = 2
        bl.parameter("theta").sp = theta_angle

        assert_that(drives["s1_axis"].sp, is_(0))
        assert_that(drives["s3_axis"].sp, is_(0.0))

        expected_det_value = 2 * spacing * tan(radians(theta_angle * 2.0))
        assert_that(drives["det_axis"].sp, is_(expected_det_value))

        assert_that(drives["det_angle_axis"].sp, is_(2*theta_angle))


class TestBeamlineValidation(unittest.TestCase):

    def test_GIVEN_two_beamline_parameters_with_same_name_WHEN_construct_THEN_error(self):
        one = EmptyBeamlineParameter("same")
        two = EmptyBeamlineParameter("same")

        assert_that(calling(Beamline).with_args([], [one, two], [], []), raises(ValueError))

    def test_GIVEN_two_modes_with_same_name_WHEN_construct_THEN_error(self):
        one = BeamlineMode("same", [])
        two = BeamlineMode("same", [])

        assert_that(calling(Beamline).with_args([], [], [], [one, two]), raises(ValueError))

    def test_GIVEN_enable_disable_parameter_with_driver_that_has_no_offset_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = Component("comp", PositionAndAngle(0, 0, 0))
        beamline_parameter = InBeamParameter("param", component)
        motor_axis = create_mock_axis("axis", 0, 0)
        driver = DisplacementDriver(component, motor_axis)

        assert_that(calling(Beamline).with_args(
            [component],
            [beamline_parameter],
            [driver],
            [mode]), raises(ValueError))

    def test_GIVEN_enable_disable_parameter_with_driver_that_has_only_angle_driver_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = Component("comp", PositionAndAngle(0, 0, 0))
        beamline_parameter = InBeamParameter("param", component)
        motor_axis = create_mock_axis("axis", 0, 0)
        driver = AngleDriver(component, motor_axis)

        assert_that(calling(Beamline).with_args(
            [component],
            [beamline_parameter],
            [driver],
            [mode]), raises(ValueError))


class TestBeamlineModeInitialization(unittest.TestCase):

    def setUp(self):
        self.nr_mode = BeamlineMode("nr", [])
        self.pnr_mode = BeamlineMode("pnr", [])

    def test_GIVEN_no_autosaved_mode_WHEN_instantiating_beamline_THEN_defaults_to_first_in_list(self):
        expected = "nr"
        ReflectometryServer.file_io.MODE_AUTOSAVE_PATH = "NONSENSICAL_PATH"
        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    def test_GIVEN_autosaved_mode_exists_WHEN_instantiating_beamline_THEN_active_mode_is_saved_mode(self):
        expected = "pnr"
        ReflectometryServer.file_io.MODE_AUTOSAVE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "mode_pnr.txt"))
        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    def test_GIVEN_autosaved_mode_does_not_exist_in_config_WHEN_instantiating_beamline_THEN_mode_defaults_to_first_in_list(self):
        expected = "nr"
        ReflectometryServer.file_io.MODE_AUTOSAVE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "mode_nonexistent.txt"))
        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    def test_GIVEN_autosaved_mode_exists_WHEN_instantiating_beamline_THEN_mode_inits_are_not_applied(self):
        ReflectometryServer.file_io.MODE_AUTOSAVE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "mode_pnr.txt"))

        with patch.object(Beamline, '_init_params_from_mode') as mock_mode_inits:
            beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        mock_mode_inits.assert_not_called()

    def test_GIVEN_default_mode_applied_WHEN_instantiating_beamline_THEN_mode_inits_are_not_applied(self):
        ReflectometryServer.file_io.MODE_AUTOSAVE_PATH = "NONSENSICAL_PATH"
        with patch.object(Beamline, '_init_params_from_mode') as mock_mode_inits:
            beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        mock_mode_inits.assert_not_called()


if __name__ == '__main__':
    unittest.main()
