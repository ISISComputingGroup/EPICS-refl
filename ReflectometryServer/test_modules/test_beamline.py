import math
import unittest

from math import tan, radians
from hamcrest import *
from mock import Mock, patch,  call
from parameterized import parameterized

from ReflectometryServer import *

from ReflectometryServer.beamline import BeamlineConfigurationInvalidException
from ReflectometryServer.exceptions import BeamlineConfigurationParkAutosaveInvalidException
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.out_of_beam import OutOfBeamSequence
from ReflectometryServer.test_modules.data_mother import DataMother, create_mock_axis, EmptyBeamlineParameter
from ReflectometryServer.beamline_constant import BeamlineConstant

from ReflectometryServer.test_modules.utils import position_and_angle, no_autosave

# Three axes under auto save, first tuple is out of beam positions,
# second tuple if initial positions
# last tuple is expected position,
# bool is whether in or out of beam
TEST_PARAMETER_POSITION_SETS = [
    ((-2, -3, -4), (-2, -3, -4), (0, 0, 0), False),  # all axes start out of beam, moving in moves to 0
    ((-2, -3, -4), (0, -3, -4), (0, -3, -4), True),  # first axes in beam others out of beam, moving in moves to current positions
    ((-2, -3, -4), (-2, 0, -4), (-2, 0, -4), True),  # middle axes in beam others out of beam, moving in moves to current positions
    ((-2, -3, -4), (-2, -3, 0), (-2, -3, 0), True),  # last axes in beam others out of beam, moving in moves to current positions
    ((-2, -3, -4), (0, -3, -4), (0, -3, -4), True),  # first axes not in beam others in beam, moving in moves to current positions
    ((-2, -3, -4), (-2, 0, -4), (-2, 0, -4), True),  # middle axes not in beam others in beam, moving in moves to current positions
    ((-2, -3, -4), (-2, -3, 0), (-2, -3, 0), True),  # last axes not in beam others in beam, moving in moves to current positions
    ((-2, -3, -4), (1, 2, 3), (1, 2, 3), True),  # all axes in the beam, move to current position
    ]


class TestComponentBeamline(unittest.TestCase):

    def setup_beamline(self, initial_mirror_angle, mirror_position, beam_start):
        jaws = Component("jaws", setup=PositionAndAngle(0, 0, 90))
        mirror = ReflectingComponent("mirror", setup=PositionAndAngle(0, mirror_position, 90))
        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(initial_mirror_angle, None, None))
        jaws3 = Component("jaws3", setup=PositionAndAngle(0, 20, 90))
        beamline = Beamline([jaws, mirror, jaws3], [], [], [BeamlineMode("mode", [])], beam_start)
        return beamline, mirror

    def test_GIVEN_beam_line_contains_one_passive_component_WHEN_beam_set_THEN_component_has_beam_out_same_as_beam_in(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("jaws", setup=PositionAndAngle(0, 2, 90))
        beamline = Beamline([jaws], [], [], [BeamlineMode("mode", [])], beam_start)

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

        mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(mirror_final_angle, None, None))
        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component index {}".format(index))

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_mirror_disabled_THEN_beam_positions_are_all_recalculated(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 45

        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)
        expected_beams = [beam_start, beam_start, beam_start]

        mirror.beam_path_set_point.axis[ChangeAxis.POSITION].park_sequence_count = 1
        mirror.beam_path_set_point.axis[ChangeAxis.POSITION].is_in_beam = False
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
        comp1.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(CorrectedReadbackUpdate(1.0, None, None))

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

    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_beam_line_WHEN_set_disabled_THEN_incoming_beam_auto_saved(self, mock_auto_save):
        mock_auto_save.read_parameter.return_value = None
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)
        bl.parameter("s1").sp = 0.1
        bl.parameter("s3").sp = 0.2
        bl.parameter("det").sp = 0.3
        bl.parameter("det_angle").sp = 0.4
        bl.active_mode = "NR"

        bl.active_mode = "DISABLED"

        calls_by_component = {call_arg[0][0]: call_arg[0][1]
                              for call_arg in mock_auto_save.write_parameter.call_args_list}
        for component in bl:
            save_name = component.name + "_sp"
            assert_that(calls_by_component[save_name],
                        is_(position_and_angle(component.beam_path_set_point._incoming_beam)),
                        "call autosaving {}".format(save_name))
            save_name = component.name + "_rbv"
            assert_that(calls_by_component[save_name],
                        is_(position_and_angle(component.beam_path_rbv._incoming_beam)),
                        "call autosaving {}".format(save_name))


class TestBeamlineValidation(unittest.TestCase):

    def test_GIVEN_two_beamline_parameters_with_same_name_WHEN_construct_THEN_error(self):
        one = EmptyBeamlineParameter("same")
        two = EmptyBeamlineParameter("same")

        assert_that(calling(Beamline).with_args([], [one, two], [], []), raises(BeamlineConfigurationInvalidException))

    def test_GIVEN_two_modes_with_same_name_WHEN_construct_THEN_error(self):
        one = BeamlineMode("same", [])
        two = BeamlineMode("same", [])

        assert_that(calling(Beamline).with_args([], [], [], [one, two]), raises(BeamlineConfigurationInvalidException))

    def test_GIVEN_enable_disable_parameter_with_driver_that_has_no_offset_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = Component("comp", PositionAndAngle(0, 0, 0))
        beamline_parameter = InBeamParameter("param", component)
        motor_axis = create_mock_axis("axis", 0, 0)
        driver = IocDriver(component, ChangeAxis.POSITION, motor_axis)

        assert_that(calling(Beamline).with_args(
            [component],
            [beamline_parameter],
            [driver],
            [mode]), raises(BeamlineConfigurationInvalidException))

    def test_GIVEN_enable_disable_parameter_with_driver_that_has_only_angle_driver_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 0))
        beamline_parameter = InBeamParameter("param", component)
        motor_axis = create_mock_axis("axis", 0, 0)
        driver = IocDriver(component, ChangeAxis.ANGLE, motor_axis)

        assert_that(calling(Beamline).with_args(
            [component],
            [beamline_parameter],
            [driver],
            [mode]), raises(BeamlineConfigurationInvalidException))

    def test_GIVEN_beamline_with_LONG_AXIS_parameter_before_POSITION_WHEN_construct_THEN_no_error(self):
        mode = BeamlineMode("mode", [])
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        beamline_parameters = [AxisParameter("param_1", component, ChangeAxis.LONG_AXIS),
                               AxisParameter("param_2", component, ChangeAxis.POSITION)]

        try:
            Beamline([component], beamline_parameters, [], [mode])
        except BeamlineConfigurationInvalidException:
            assert_that(True, is_(False), "Beamline construction raised unexpected error")

    def test_GIVEN_beamline_with_POSITION_parameter_before_LONG_AXIS_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        beamline_parameters = [AxisParameter("param_1", component, ChangeAxis.POSITION),
                               AxisParameter("param_2", component, ChangeAxis.LONG_AXIS)]
        assert_that(calling(Beamline).with_args(
            [component],
            beamline_parameters,
            [],
            [mode]), raises(BeamlineConfigurationInvalidException))

    def test_GIVEN_beamline_with_LONG_AXIS_driver_before_POSITION_WHEN_construct_THEN_no_error(self):
        mode = BeamlineMode("mode", [])
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        motor_axis = [create_mock_axis("axis_1", 0, 0),
                      create_mock_axis("axis_2", 0, 0)]
        drivers = [IocDriver(component, ChangeAxis.LONG_AXIS, motor_axis[0]),
                   IocDriver(component, ChangeAxis.POSITION, motor_axis[1])]

        try:
            Beamline([component], [], drivers, [mode])
        except BeamlineConfigurationInvalidException:
            assert_that(True, is_(False), "Beamline construction raised unexpected error")

    def test_GIVEN_beamline_with_POSITION_driver_before_LONG_AXIS_WHEN_construct_THEN_error(self):
        mode = BeamlineMode("mode", [])
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        motor_axis = [create_mock_axis("axis_1", 0, 0),
                      create_mock_axis("axis_2", 0, 0)]
        drivers = [IocDriver(component, ChangeAxis.POSITION, motor_axis[0]),
                   IocDriver(component, ChangeAxis.LONG_AXIS, motor_axis[1])]
        assert_that(calling(Beamline).with_args(
            [component],
            [],
            drivers,
            [mode]), raises(BeamlineConfigurationInvalidException))


class TestBeamlineModeInitialization(unittest.TestCase):

    def setUp(self):
        self.nr_mode = BeamlineMode("nr", [])
        self.pnr_mode = BeamlineMode("pnr", [])

    @patch('ReflectometryServer.beamline.mode_autosave')
    def test_GIVEN_no_autosaved_mode_WHEN_instantiating_beamline_THEN_defaults_to_first_in_list(self, mode_autosave):
        mode_autosave.read_parameter.return_value = None  # e.g. no value
        expected = "nr"
        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    @patch('ReflectometryServer.beamline.mode_autosave')
    def test_GIVEN_autosaved_mode_exists_WHEN_instantiating_beamline_THEN_active_mode_is_saved_mode(self, mode_autosave):

        expected = "pnr"
        mode_autosave.read_parameter.return_value = expected

        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    @patch('ReflectometryServer.beamline.mode_autosave')
    def test_GIVEN_autosaved_mode_does_not_exist_in_config_WHEN_instantiating_beamline_THEN_mode_defaults_to_first_in_list(self, mode_autosave):
        expected = "nr"
        mode_autosave.read_parameter.return_value = "mode_nonexistent"
        beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        actual = beamline.active_mode

        self.assertEqual(expected, actual)

    @patch('ReflectometryServer.beamline.mode_autosave')
    def test_GIVEN_autosaved_mode_exists_WHEN_instantiating_beamline_THEN_mode_inits_are_not_applied(self, mode_autosave):
        mode_autosave.read_parameter.return_value = "pnr"

        with patch.object(Beamline, '_init_params_from_mode') as mock_mode_inits:
            beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        mock_mode_inits.assert_not_called()

    @patch('ReflectometryServer.beamline.mode_autosave')
    def test_GIVEN_default_mode_applied_WHEN_instantiating_beamline_THEN_mode_inits_are_not_applied(self, mode_autosave):

        mode_autosave.read_parameter.return_value = None
        with patch.object(Beamline, '_init_params_from_mode') as mock_mode_inits:
            beamline = Beamline([], [], [], [self.nr_mode, self.pnr_mode])

        mock_mode_inits.assert_not_called()

    @patch('ReflectometryServer.beamline.mode_autosave')
    @patch('ReflectometryServer.beam_path_calc.disable_mode_autosave')
    def test_GIVEN_beam_line_with_disable_autosave_position_WHEN_init_THEN_incoming_beams_set_correctly_on_start(self, mock_disable_mode_auto_save, mock_mode_auto_save):

        mock_mode_auto_save.read_parameter.return_value = "DISABLED"

        s1_comp_name = "s1_comp"
        s3_comp_name = "s3_comp"
        detector_comp_name = "Detector_comp"
        theta_comp_name = "ThetaComp_comp"
        autosave_values = {
            s1_comp_name: PositionAndAngle(0, 1, 0),
            s3_comp_name: PositionAndAngle(0, 1, 1),
            detector_comp_name: PositionAndAngle(2, 1, 4),
            theta_comp_name: PositionAndAngle(3, 2, 1)
        }

        def autosave_value(key, default):
            if key.endswith("_sp"):
                return autosave_values.get(key[:-len("_sp")], default)
            else:
                return None

        mock_disable_mode_auto_save.read_parameter.side_effect = autosave_value
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing, initilise_mode_nr=False)

        result = {comp.name: (comp.beam_path_set_point._incoming_beam, comp.beam_path_set_point.get_outgoing_beam())
                  for comp in bl}

        assert_that(result[s1_comp_name][0], is_(position_and_angle(autosave_values[s1_comp_name])))
        assert_that(result[s3_comp_name][0], is_(position_and_angle(autosave_values[s3_comp_name])))
        assert_that(result[theta_comp_name][0], is_(position_and_angle(autosave_values[theta_comp_name])))

        # The detector incoming beam should be the same as the outgoing beam for theta because theta controls the
        # detector height
        assert_that(result[detector_comp_name][0], is_(position_and_angle(result[theta_comp_name][1])))


class TestRealisticWithAutosaveInit(unittest.TestCase):

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_theta_at_0_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 22.5
        expected_theta = 0
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_theta_at_non_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 22.5
        expected_theta = 2
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_det_offset_at_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 22.5
        expected_theta = 0
        expected_det_offset = 0
        file_io.read_parameter.return_value = expected_det_offset

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, autosave_theta_not_offset=False)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_det_offset_at_non_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 22.5
        expected_theta = 0
        expected_det_offset = 1
        file_io.read_parameter.return_value = expected_det_offset

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, expected_det_offset, autosave_theta_not_offset=False)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(expected_det_offset, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(expected_det_offset, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_with_nonzero_beam_start_with_all_values_at_0_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        beam_start_angle = -2.3
        expected_sm_angle = 0
        expected_theta = 0
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, beam_angle=beam_start_angle)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_with_nonzero_beam_start_where_autosave_theta_at_0_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        beam_start_angle = -2.3
        expected_sm_angle = 22.5
        expected_theta = 0
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, beam_angle=beam_start_angle)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_with_nonzero_beam_start_where_autosave_theta_at_non_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        beam_start_angle = -2.3
        expected_sm_angle = 22.5
        expected_theta = 2
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, beam_angle=beam_start_angle)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_with_nonzero_beam_start_where_autosave_det_offset_at_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        beam_start_angle = -2.3
        expected_sm_angle = 22.5
        expected_theta = 0
        expected_det_offset = 0
        file_io.read_parameter.return_value = expected_det_offset

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, autosave_theta_not_offset=False, beam_angle=beam_start_angle)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(0, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(0, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_with_nonzero_beam_start_where_autosave_det_offset_at_non_zero_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        beam_start_angle = -2.3
        expected_sm_angle = 22.5
        expected_theta = 0
        expected_det_offset = 1
        file_io.read_parameter.return_value = expected_det_offset

        bl, drives = DataMother.beamline_sm_theta_detector(expected_sm_angle, expected_theta, expected_det_offset, autosave_theta_not_offset=False, beam_angle=beam_start_angle)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("det_pos").sp, is_(close_to(expected_det_offset, 1e-6)), "det position SP")
        assert_that(bl.parameter("det_angle").sp, is_(close_to(0, 1e-6)), "det angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("det_pos").sp_rbv, is_(close_to(expected_det_offset, 1e-6)), "det position SP RBV")
        assert_that(bl.parameter("det_angle").sp_rbv, is_(close_to(0, 1e-6)), "det angle SP RBV")


class TestRealisticWithAutosaveInitAndBench(unittest.TestCase):

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_theta_at_0p1_and_bench_offset_0_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 0
        expected_theta = 0.1
        driver_bench_offset = 0
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_bench(expected_sm_angle, expected_theta, driver_bench_offset)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("bench_angle").sp, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("bench_angle").sp_rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP RBV")

        assert_that(bl.parameter("sm_angle").rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle RBV")
        assert_that(bl.parameter("theta").rbv, is_(close_to(expected_theta, 1e-6)), "theta RBV")
        assert_that(bl.parameter("bench_angle").rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_theta_at_0p1_and_bench_offset_2_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 0
        expected_theta = 0.1
        driver_bench_offset = 2
        file_io.read_parameter.return_value = expected_theta

        bl, drives = DataMother.beamline_sm_theta_bench(expected_sm_angle, expected_theta, driver_bench_offset)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("bench_angle").sp, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("bench_angle").sp_rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP RBV")

        assert_that(bl.parameter("sm_angle").rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle RBV")
        assert_that(bl.parameter("theta").rbv, is_(close_to(expected_theta, 1e-6)), "theta RBV")
        assert_that(bl.parameter("bench_angle").rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_bench_offset_2_and_theta_0p1_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 0
        expected_theta = 0.1
        driver_bench_offset = 2
        file_io.read_parameter.return_value = driver_bench_offset

        bl, drives = DataMother.beamline_sm_theta_bench(expected_sm_angle, expected_theta, driver_bench_offset, autosave_bench_not_theta=True)

        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("bench_angle").sp, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("bench_angle").sp_rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle SP RBV")

        assert_that(bl.parameter("sm_angle").rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle RBV")
        assert_that(bl.parameter("theta").rbv, is_(close_to(expected_theta, 1e-6)), "theta RBV")
        assert_that(bl.parameter("bench_angle").rbv, is_(close_to(driver_bench_offset, 1e-6)), "bench angle RBV")

    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_beam_line_where_autosave_ang_offset_2_and_theta_0p1_WHEN_init_THEN_beamline_is_at_given_place(self, file_io):
        expected_sm_angle = 0
        expected_theta = 0.1
        angle_offset = 2
        file_io.read_parameter.return_value = angle_offset

        bl, drives = DataMother.beamline_sm_theta_ang_det(expected_sm_angle, expected_theta, angle_offset, autosave_bench_not_theta=True)
        for drive in drives.values():
            drive.trigger_rbv_change()
        assert_that(bl.parameter("sm_angle").sp, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP")
        assert_that(bl.parameter("theta").sp, is_(close_to(expected_theta, 1e-6)), "theta SP")
        assert_that(bl.parameter("comp_angle").sp, is_(close_to(angle_offset, 1e-6)), "comp angle SP")

        assert_that(bl.parameter("sm_angle").sp_rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle SP RBV")
        assert_that(bl.parameter("theta").sp_rbv, is_(close_to(expected_theta, 1e-6)), "theta SP RBV")
        assert_that(bl.parameter("comp_angle").sp_rbv, is_(close_to(angle_offset, 1e-6)), "comp angle SP RBV")

        assert_that(bl.parameter("sm_angle").rbv, is_(close_to(expected_sm_angle, 1e-6)), "sm angle RBV")
        assert_that(bl.parameter("theta").rbv, is_(close_to(expected_theta, 1e-6)), "theta RBV")
        assert_that(bl.parameter("comp_angle").rbv, is_(close_to(angle_offset, 1e-6)), "comp angle RBV")

class TestBeamlineReadOnlyParameters(unittest.TestCase):

    def setup_beamline(self, parameters):

        beamline = Beamline([], [], [], [], beamline_constants=parameters)
        return beamline

    def test_GIVEN_there_are_no_beamline_constant_set_empty_list_WHEN_get_beamline_constant_THEN_empty(self):

        beamline = self.setup_beamline([])

        result = beamline.beamline_constants

        assert_that(result, is_([]))

    def test_GIVEN_there_are_no_beamline_constant_set_using_none_WHEN_get_beamline_constant_THEN_empty(self):

        beamline = self.setup_beamline(None)

        result = beamline.beamline_constants

        assert_that(result, is_([]))

    def test_GIVEN_there_are_beamline_constant_set_WHEN_get_beamline_constant_THEN_parameters_returned(self):
        expected_parameters = [
            BeamlineConstant("NAME", 2, "description")
        ]
        beamline = self.setup_beamline(expected_parameters)

        result = beamline.beamline_constants

        assert_that(result, is_(expected_parameters))


class TestComponentOutOfBeam(unittest.TestCase):

    @no_autosave
    def setUp(self):
        self.comp = Component("test_component", PositionAndAngle(0, 0, 90))
        self.IN_BEAM_VALUE = 0
        self.OUT_OF_BEAM_VALUE = -5

    @parameterized.expand([(ChangeAxis.PHI,), (ChangeAxis.CHI,), (ChangeAxis.PSI,), (ChangeAxis.TRANS,), (ChangeAxis.HEIGHT,), (ChangeAxis.POSITION,)])
    def test_GIVEN_driver_on_component_has_no_out_of_beam_position_THEN_appropriate_change_axes_reports_not_having_out_of_beam_position(self, change_axis_to_set):
        IocDriver(self.comp, change_axis_to_set, create_mock_axis("axis", 0, 1), out_of_beam_positions=None)

        for change_axis, component_axis in self.comp.beam_path_rbv.axis.items():
            assert_that(component_axis.park_sequence_count, is_(0))

        for change_axis, component_axis in self.comp.beam_path_set_point.axis.items():
            assert_that(component_axis.park_sequence_count, is_(0))

    @parameterized.expand([(ChangeAxis.PHI,), (ChangeAxis.CHI,), (ChangeAxis.PSI,), (ChangeAxis.TRANS,), (ChangeAxis.HEIGHT,), (ChangeAxis.POSITION,)])
    def test_GIVEN_driver_on_component_has_out_of_beam_position_THEN_appropriate_change_axis_report_having_out_of_beam_position(self, change_axis_to_set):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        IocDriver(self.comp, change_axis_to_set, create_mock_axis("axis", 0, 1),
                           out_of_beam_positions=[out_of_beam_position])

        for change_axis, component_axis in self.comp.beam_path_rbv.axis.items():
            if change_axis == change_axis_to_set:
                assert_that(component_axis.park_sequence_count, is_(1))
            else:
                assert_that(component_axis.park_sequence_count, is_(0))

        for change_axis, component_axis in self.comp.beam_path_set_point.axis.items():
            if change_axis == change_axis_to_set:
                assert_that(component_axis.park_sequence_count, is_(1))
            else:
                assert_that(component_axis.park_sequence_count, is_(0))

    @parameterized.expand([(ChangeAxis.PHI,), (ChangeAxis.CHI,), (ChangeAxis.PSI,), (ChangeAxis.TRANS,), (ChangeAxis.HEIGHT,), (ChangeAxis.POSITION,)])
    def test_GIVEN_component_with_driver_with_out_of_beam_position_WHEN_motor_is_in_beam_THEN_component_axis_reports_in_beam(self, change_axis_to_set):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        motor_axis = create_mock_axis("axis", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, change_axis_to_set, motor_axis, out_of_beam_positions=[out_of_beam_position])
        expected = True

        motor_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.axis[change_axis_to_set].is_in_beam

        assert_that(actual, is_(expected))

    @parameterized.expand([(ChangeAxis.PHI,), (ChangeAxis.CHI,), (ChangeAxis.PSI,), (ChangeAxis.TRANS,), (ChangeAxis.HEIGHT,), (ChangeAxis.POSITION,)])
    def test_GIVEN_component_with_driver_with_out_of_beam_position_WHEN_motor_is_out_of_beam_THEN_component_axis_reports_out_of_beam(self, change_axis_to_set):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        motor_axis = create_mock_axis("axis", self.OUT_OF_BEAM_VALUE, 1)
        IocDriver(self.comp, change_axis_to_set, motor_axis, out_of_beam_positions=[out_of_beam_position])
        expected = False

        motor_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.axis[change_axis_to_set].is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_one_driver_with_out_of_beam_position_WHEN_axis_is_not_in_beam_THEN_in_beam_rbv_is_false(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.OUT_OF_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        expected = False

        chi_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_one_driver_with_out_of_beam_position_WHEN_axis_is_in_beam_THEN_in_beam_rbv_is_true(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        expected = True

        chi_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_multiple_drivers_with_out_of_beam_position_WHEN_all_are_in_beam_THEN_in_beam_rbv_is_true(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.IN_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        expected = True

        chi_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_multiple_axes_with_out_of_beam_position_WHEN_none_are_in_beam_THEN_in_beam_rbv_is_false(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.OUT_OF_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.OUT_OF_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        expected = False

        chi_axis.trigger_rbv_change()
        psi_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_multiple_axes_with_out_of_beam_position_WHEN_one_is_in_beam_THEN_in_beam_rbv_is_true(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.OUT_OF_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        expected = True

        chi_axis.trigger_rbv_change()
        psi_axis.trigger_rbv_change()
        actual = self.comp.beam_path_rbv.is_in_beam

        assert_that(actual, is_(expected))

    def test_GIVEN_component_partially_in_beam_WHEN_setting_new_setpoint_for_axis_out_of_beam_THEN_driver_moves(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.IN_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.OUT_OF_BEAM_VALUE, 1)
        chi_driver = IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        psi_driver = IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        chi_axis.sp = self.IN_BEAM_VALUE
        psi_axis.sp = self.OUT_OF_BEAM_VALUE
        chi_driver.initialise_setpoint()
        psi_driver.initialise_setpoint()

        expected = self.IN_BEAM_VALUE

        self.comp.beam_path_set_point.axis[ChangeAxis.PSI].set_displacement(CorrectedReadbackUpdate(self.IN_BEAM_VALUE, None, None))
        psi_driver.perform_move(1)
        actual = psi_axis.sp

        assert_that(actual, is_(expected))

    def test_GIVEN_component_with_axis_with_out_of_beam_position_WHEN_in_beam_sp_changes_THEN_only_axis_with_out_of_beam_position_marked_as_changed(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.IN_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.IN_BEAM_VALUE, 1)
        phi_axis = create_mock_axis("phi", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PHI, phi_axis, out_of_beam_positions=None)

        self.comp.beam_path_set_point.is_in_beam = False

        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.CHI].is_changed, is_(True))
        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.PSI].is_changed, is_(True))
        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.PHI].is_changed, is_(False))

    def test_GIVEN_component_with_multiple_axes_with_out_of_beam_position_WHEN_setting_sp_THEN_in_beam_sp_moved_to_for_all_axes_with_out_of_beam_position(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.IN_BEAM_VALUE, 1)
        psi_axis = create_mock_axis("psi", self.IN_BEAM_VALUE, 1)
        phi_axis = create_mock_axis("phi", self.IN_BEAM_VALUE, 1)
        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PSI, psi_axis, out_of_beam_positions=[out_of_beam_position])
        IocDriver(self.comp, ChangeAxis.PHI, phi_axis, out_of_beam_positions=None)

        self.comp.beam_path_set_point.is_in_beam = False

        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.CHI].is_in_beam, is_(False))
        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.PSI].is_in_beam, is_(False))
        assert_that(self.comp.beam_path_set_point.axis[ChangeAxis.PHI].is_in_beam, is_(True))

    def test_GIVEN_component_WHEN_adding_driver_with_out_of_beam_position_THEN_inbeam_parameter_listens_to_relevant_axis(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.OUT_OF_BEAM_VALUE, 1)
        in_beam_param = InBeamParameter("in_beam", self.comp)

        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        chi_axis.trigger_rbv_change()

        assert_that(in_beam_param.rbv, is_(False))

    def test_GIVEN_inbeam_parameter_on_component_WHEN_adding_driver_with_out_of_beam_position_THEN_parameter_gets_init_value(self):
        out_of_beam_position = OutOfBeamPosition(self.OUT_OF_BEAM_VALUE)
        chi_axis = create_mock_axis("chi", self.OUT_OF_BEAM_VALUE, 1)
        in_beam_param = InBeamParameter("in_beam", self.comp)

        IocDriver(self.comp, ChangeAxis.CHI, chi_axis, out_of_beam_positions=[out_of_beam_position])
        chi_axis.trigger_rbv_change()

        assert_that(in_beam_param.rbv, is_(False))

    def test_GIVEN_inbeam_parameter_on_detector_WHEN_init_with_angle_in_beam_THEN_theta_is_defined(self):
        out_of_beam_pos = -5
        det_in, theta = DataMother.beamline_theta_detector(out_of_beam_pos, out_of_beam_pos, -2, 0)

        assert_that(det_in.sp, is_(True))
        assert_that(theta.sp, is_(0.0))

    def test_GIVEN_inbeam_parameter_on_detector_WHEN_init_with_pos_in_beam_THEN_theta_is_defined(self):
        out_of_beam_pos = -5
        det_in, theta = DataMother.beamline_theta_detector(-2, 0, out_of_beam_pos, out_of_beam_pos)

        assert_that(det_in.sp, is_(True))
        assert_that(theta.sp, is_(0.0))

    def test_GIVEN_inbeam_parameter_on_detector_WHEN_init_with_both_out_of_beam_THEN_theta_sp_is_0(self):
        out_of_beam_pos = -5
        out_of_beam_pos_z = -2
        det_in, theta = DataMother.beamline_theta_detector(out_of_beam_pos_z, out_of_beam_pos_z, out_of_beam_pos, out_of_beam_pos)

        assert_that(det_in.sp, is_(False))
        assert_that(theta.sp, is_(0))


class TestComponentOutOfBeamFullBeamline(unittest.TestCase):

    def setUp(self) -> None:
        ConfigHelper.reset()

    @parameterized.expand([((-2, -3, -4), (-2, -3, -4), (-2, -3, -4), False),  # all axes start out of beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (0, -3, -4), (0, -3, -4), True),  # first axes in beam others out of beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (-2, 0, -4), (-2, 0, -4), True),  # middle axes in beam others out of beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (-2, -3, 0), (-2, -3, 0), True), # last axes in beam others out of beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (0, -3, -4), (0, -3, -4), True), # first axes not in beam others in beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (-2, 0, -4), (-2, 0, -4), True), # middle axes not in beam others in beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (-2, -3, 0), (-2, -3, 0), True), # last axes not in beam others in beam, moving in moves to autosaved positions
                           ((-2, -3, -4), (1, 2, 3), (1, 2, 3), True),  # all axes in the beam, move to current position
                          ])
    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_component_with_multiple_axes_out_of_beam_with_autosave_WHEN_init_and_move_in_THEN_component_moves_to_expected_palce(self,
           out_of_beam_positions, init_positions, expected_positions,
           expected_initial_inbeam, mock_autosave):

        mock_autosave.read_parameter.side_effect = expected_positions
        axis_ang, axis_phi, axis_pos, inbeam = self.setup_beamline(out_of_beam_positions, init_positions)
        assert_that(inbeam.sp, is_(expected_initial_inbeam))

        inbeam.sp = True

        assert_that(axis_pos.rbv, is_(expected_positions[0]))
        assert_that(axis_ang.rbv, is_(expected_positions[1]))
        assert_that(axis_phi.rbv, is_(expected_positions[2]))

    def setup_beamline(self, out_of_beam_positions, init_positions, autosave_axes=True, autosave_inbeam=False):
        # Setup is in or out of the beam and with autosaved positions, on move should move to autosaved positions
        mode = add_mode("MODE")
        comp = add_component(TiltingComponent("comp", PositionAndAngle(0, 0, 90)))

        param_pos = add_parameter(AxisParameter("pos", comp, ChangeAxis.POSITION, autosave=autosave_axes), [mode])
        param_ang = add_parameter(AxisParameter("angle", comp, ChangeAxis.ANGLE, autosave=autosave_axes), [mode])
        param_phi = add_parameter(AxisParameter("phi", comp, ChangeAxis.PHI, autosave=autosave_axes), [mode])
        inbeam = add_parameter(InBeamParameter("in_beam", comp, autosave=autosave_inbeam), [mode])
        axis_pos = create_mock_axis("pos_axis", init_positions[0], 1)
        axis_ang = create_mock_axis("ang_axis", init_positions[1], 1)
        axis_phi = create_mock_axis("phi_axis", init_positions[2], 1)
        driver_pos = add_driver(IocDriver(comp, ChangeAxis.POSITION, axis_pos,
                                          out_of_beam_positions=[OutOfBeamPosition(out_of_beam_positions[0])]))
        driver_ang = add_driver(IocDriver(comp, ChangeAxis.ANGLE, axis_ang,
                                          out_of_beam_positions=[OutOfBeamPosition(out_of_beam_positions[1])]))
        driver_phi = add_driver(IocDriver(comp, ChangeAxis.PHI, axis_phi,
                                          out_of_beam_positions=[OutOfBeamPosition(out_of_beam_positions[2])]))
        beamline = get_configured_beamline()
        assert_that(axis_ang.last_set_point_set, is_(None))  # set point wasn't set during init
        assert_that(axis_pos.last_set_point_set, is_(None))  # set point wasn't set during init
        assert_that(axis_phi.last_set_point_set, is_(None))  # set point wasn't set during init
        return axis_ang, axis_phi, axis_pos, inbeam

    @parameterized.expand(TEST_PARAMETER_POSITION_SETS)
    def test_GIVEN_component_with_multiple_axes_out_of_beam_no_auto_save_WHEN_init_and_move_in_THEN_component_moves_to_expected_palce(self,
          out_of_beam_positions, init_positions, expected_positions, expected_initial_inbeam):

        axis_ang, axis_phi, axis_pos, inbeam = self.setup_beamline(out_of_beam_positions, init_positions, False)

        assert_that(inbeam.sp, is_(expected_initial_inbeam))

        inbeam.sp = True

        assert_that(axis_pos.rbv, is_(expected_positions[0]))
        assert_that(axis_ang.rbv, is_(expected_positions[1]))
        assert_that(axis_phi.rbv, is_(expected_positions[2]))

    @parameterized.expand(TEST_PARAMETER_POSITION_SETS)
    @patch("ReflectometryServer.parameters.param_float_autosave")
    def test_GIVEN_component_with_multiple_axes_out_of_beam_with_autosave_not_no_value_WHEN_init_and_move_in_THEN_component_moves_to_expected_palce(self,
          out_of_beam_positions, init_positions, expected_positions, expected_initial_inbeam, mock_autosave):

        mock_autosave.read_parameter.side_effect = [None, None, None]
        axis_ang, axis_phi, axis_pos, inbeam = self.setup_beamline(out_of_beam_positions, init_positions, True)

        assert_that(inbeam.sp, is_(expected_initial_inbeam))

        inbeam.sp = True

        assert_that(axis_pos.rbv, is_(expected_positions[0]))
        assert_that(axis_ang.rbv, is_(expected_positions[1]))
        assert_that(axis_phi.rbv, is_(expected_positions[2]))

    @patch("ReflectometryServer.beam_path_calc.parking_index_autosave")
    @patch("ReflectometryServer.parameters.param_bool_autosave")
    def test_GIVEN_component_with_multiple_axes_out_of_beam_with_autosave_only_on_in_beam_WHEN_init_and_move_in_THEN_component_moves_to_expected_place_and_do_not_move_on_init(self,
           mock_autosave, mock_parking_index):

        expected_position = 0
        expected_initial_inbeam = False
        mock_autosave.read_parameter.side_effect = [False]
        mock_parking_index.read_parameter.return_value = None
        axis_ang, axis_phi, axis_pos, inbeam = self.setup_beamline((-2, -3, -4), (-2, -3, -4), False, True)

        assert_that(inbeam.sp, is_(expected_initial_inbeam))
        for axis in [axis_pos, axis_ang, axis_phi]:
            axis.trigger_rbv_change()
        assert_that(axis_ang.last_set_point_set, is_(None))  # set point wasn't set during init
        assert_that(axis_pos.last_set_point_set, is_(None))  # set point wasn't set during init
        assert_that(axis_phi.last_set_point_set, is_(None))  # set point wasn't set during init

        inbeam.sp = True

        assert_that(axis_ang.rbv, is_(expected_position))
        assert_that(axis_pos.rbv, is_(expected_position))
        assert_that(axis_phi.rbv, is_(expected_position))

class TestComponentParkingSequence(unittest.TestCase):

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=None))
    def test_GIVEN_component_with_one_axis_and_parking_sequence_WHEN_out_of_beam_THEN_component_moves_to_correct_places(self):
        pos1 = -3
        pos2 = -6
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis = create_mock_axis("axis_motor", 0, 1)
        driver = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis, out_of_beam_positions=[OutOfBeamSequence([pos1, pos2])])
        beamline = Beamline([comp], [parameter], [driver], [BeamlineMode("mode", [])])

        parameter.sp = False

        assert_that(mock_axis.sp, is_(pos2))
        assert_that(parameter.rbv, is_(False))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=None))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_with_repeat_WHEN_out_of_beam_THEN_component_moves_to_correct_places(self):
        pos1 = -3
        expected_sequence = [4, 6, 8]
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)
        mock_axis2 = create_mock_axis("axis_motor2", 0, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence([pos1, pos1, pos1])])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(expected_sequence)])
        beamline = Beamline([comp], [parameter], [driver1, driver2], [BeamlineMode("mode", [])])

        parameter.sp = False

        assert_that(mock_axis1.all_setpoints, is_([pos1]))
        assert_that(mock_axis2.all_setpoints, is_(expected_sequence))
        assert_that(parameter.rbv, is_(False))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=None))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_with_none_WHEN_out_of_beam_THEN_component_moves_to_correct_places(self):
        pos1 = -3
        expected_sequence = [4, 6, 8]
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)
        mock_axis2 = create_mock_axis("axis_motor2", 0, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence([None, None, pos1])])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(expected_sequence)])
        beamline = Beamline([comp], [parameter], [driver1, driver2], [BeamlineMode("mode", [])])
        mock_axis1.trigger_rbv_change()
        mock_axis2.trigger_rbv_change()

        parameter.sp = False

        assert_that(mock_axis1.all_setpoints, is_([pos1]))
        assert_that(mock_axis2.all_setpoints, is_(expected_sequence))
        assert_that(parameter.rbv, is_(False))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave')
    def test_GIVEN_sequence_and_autosave_position_not_at_end_of_sequence_WHEN_init_THEN_init_error_and_autosave_overwriten(self, auto_save):
        auto_save.read_parameter.return_value = 1
        comp = Component("comp name", PositionAndAngle(0, 0, 90))
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)

        with self.assertRaises(BeamlineConfigurationParkAutosaveInvalidException):
            IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence([1, 2, 3])])

        auto_save.write_parameter.assert_called()

    @parameterized.expand([(None, [1]),  # unparked
                           (0, [1]),  # last value in length 1 sequence
                           (1, [1, 2]),  # last value in length 2 sequence
                           (5, [1, 2])   # after the last value in a sequence (it may be a different sequence this parked in)
                           ])
    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave')
    def test_GIVEN_sequence_and_autosave_position_ok_WHEN_init_THEN_no_error(self, auto_save_value, sequence, auto_save):
        auto_save.read_parameter.return_value = auto_save_value
        comp = Component("comp name", PositionAndAngle(0, 0, 90))
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)

        IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence(sequence)])

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=None))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_WHEN_out_of_beam_and_then_in_beam_THEN_component_moves_to_correct_places(self):
        sequence1 = [4, 6, 8]
        expected_motor1_sps = [4, 6, 8, 6, 4, 0]  # 0 is final in beam position
        sequence2 = [5, 7, 9]
        expected_motor2_sps = [5, 7, 9, 7, 5, 0]
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)
        mock_axis2 = create_mock_axis("axis_motor2", 0, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence(sequence1)])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(sequence2)])
        beamline = Beamline([comp], [parameter], [driver1, driver2], [BeamlineMode("mode", [])])

        parameter.sp = False
        parameter.sp = True

        assert_that(mock_axis1.all_setpoints, is_(expected_motor1_sps))
        assert_that(mock_axis2.all_setpoints, is_(expected_motor2_sps))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=None))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_with_repeated_entry_at_end_WHEN_out_of_beam_and_then_in_beam_THEN_component_moves_to_correct_places(self):
        sequence1 = [4, 6, 6]
        expected_motor1_sps = [4, 6, 4, 0]
        sequence2 = [3, 5, 7]
        expected_motor2_sps = [3, 5, 7, 5, 3, 0]
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis1 = create_mock_axis("axis_motor1", 0, 1)
        mock_axis2 = create_mock_axis("axis_motor2", 0, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence(sequence1)])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(sequence2)])
        beamline = Beamline([comp], [parameter], [driver1, driver2], [BeamlineMode("mode", [])])

        parameter.sp = False
        parameter.sp = True

        assert_that(mock_axis1.all_setpoints, is_(expected_motor1_sps))
        assert_that(mock_axis2.all_setpoints, is_(expected_motor2_sps))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=2))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_WHEN_motors_out_of_beam_and_init_THEN_motors_do_not_move(self):
        last_pos1 = 6
        sequence1 = [4, 1, last_pos1]

        last_pos2 = 5
        sequence2 = [3, 2, last_pos2]

        comp = Component("comp", PositionAndAngle(0, 0, 90))
        parameter = InBeamParameter("val", comp)
        mock_axis1 = create_mock_axis("axis_motor1", last_pos1, 1)
        mock_axis2 = create_mock_axis("axis_motor2", last_pos2, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence(sequence1)])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(sequence2)])
        comp.beam_path_set_point.in_beam_manager.add_rbv_in_beam_manager(comp.beam_path_rbv.in_beam_manager)
        driver1.initialise_setpoint()
        mock_axis1.trigger_rbv_change()
        mock_axis2.trigger_rbv_change()  # this is not quite how it happens on start up where this is generated during
                                         # the initalise but it is good enough

        assert_that(mock_axis1.all_setpoints, is_([]))
        assert_that(mock_axis2.all_setpoints, is_([]))

    @patch('ReflectometryServer.beam_path_calc.parking_index_autosave.read_parameter', new=Mock(return_value=2))
    def test_GIVEN_component_with_two_axes_and_parking_sequence_WHEN_motors_out_of_beam_and_init_with_autosaved_bean_out_THEN_motors_do_not_move(self):
        last_pos1 = 6
        sequence1 = [4, 1, last_pos1]

        last_pos2 = 5
        sequence2 = [3, 2, last_pos2]

        comp = Component("comp", PositionAndAngle(0, 0, 90))
        with patch('ReflectometryServer.parameters.param_bool_autosave.read_parameter') as param_autosave:
            param_autosave.return_value = True
            parameter = InBeamParameter("val", comp, autosave=True)
        mock_axis1 = create_mock_axis("axis_motor1", last_pos1, 1)
        mock_axis2 = create_mock_axis("axis_motor2", last_pos2, 1)
        driver1 = IocDriver(comp, ChangeAxis.HEIGHT, mock_axis1, out_of_beam_positions=[OutOfBeamSequence(sequence1)])
        driver2 = IocDriver(comp, ChangeAxis.TRANS, mock_axis2, out_of_beam_positions=[OutOfBeamSequence(sequence2)])
        comp.beam_path_set_point.in_beam_manager.add_rbv_in_beam_manager(comp.beam_path_rbv.in_beam_manager)
        driver1.initialise_setpoint()
        mock_axis1.trigger_rbv_change()
        mock_axis2.trigger_rbv_change()  # this is not quite how it happens on start up where this is generated during
                                         # the initalise but it is good enough

        assert_that(mock_axis1.all_setpoints, is_([]))
        assert_that(mock_axis2.all_setpoints, is_([]))


if __name__ == '__main__':
    unittest.main()
