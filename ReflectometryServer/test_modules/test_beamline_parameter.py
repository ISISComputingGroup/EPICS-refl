import os
import unittest
from math import isnan

from hamcrest import *
from mock import Mock
from parameterized import parameterized

from ReflectometryServer import *
from ReflectometryServer.beamline import BeamlineConfigurationInvalidException
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.parameters import ParameterReadbackUpdate
from ReflectometryServer.pv_wrapper import ReadbackUpdate

from data_mother import DataMother, create_mock_axis
from server_common.channel_access import AlarmSeverity, AlarmStatus
from utils import position, DEFAULT_TEST_TOLERANCE, create_parameter_with_initial_value, setup_autosave


class TestBeamlineParameter(unittest.TestCase):

    def test_GIVEN_theta_WHEN_set_set_point_THEN_sample_hasnt_moved(self):
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        mirror_pos = -100
        sample.beam_path_set_point.set_angular_displacement(mirror_pos)
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set

        assert_that(theta.sp, is_(theta_set))
        assert_that(sample.beam_path_set_point.get_angular_displacement(), is_(mirror_pos))

    def test_GIVEN_theta_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_sample_is_at_setpoint_postion(self):

        theta_set = 10.0
        expected_sample_angle = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.set_angular_displacement(mirror_pos)
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set
        theta.move = 1
        result = theta.sp_rbv

        assert_that(result, is_(theta_set))
        assert_that(sample.beam_path_set_point.get_angular_displacement(), is_(expected_sample_angle))

    def test_GIVEN_theta_set_WHEN_set_point_set_and_move_THEN_readback_is_as_original_value_but_setpoint_is_new_value(self):

        original_theta = 1.0
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.set_angular_displacement(mirror_pos)
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)
        theta.sp = original_theta

        theta.sp_no_move = theta_set
        result = theta.sp_rbv

        assert_that(result, is_(original_theta))
        assert_that(theta.sp, is_(theta_set))

    def test_GIVEN_theta_and_a_set_but_no_move_WHEN_get_changed_THEN_changed_is_true(self):

        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set
        result = theta.sp_changed

        assert_that(result, is_(True))

    def test_GIVEN_theta_and_a_set_and_move_WHEN_get_changed_THEN_changed_is_false(self):

        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set
        theta.move = 1
        result = theta.sp_changed

        assert_that(result, is_(False))

    def test_GIVEN_reflection_angle_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_sample_is_at_setpoint_postion(self):

        angle_set = 10.0
        expected_sample_angle = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.set_angular_displacement(mirror_pos)
        reflection_angle = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        reflection_angle.sp_no_move = angle_set
        reflection_angle.move = 1
        result = reflection_angle.sp_rbv

        assert_that(result, is_(angle_set))
        assert_that(sample.beam_path_set_point.get_angular_displacement(), is_(expected_sample_angle))

    def test_GIVEN_jaw_height_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_jaws_are_at_setpoint_postion(self):

        height_set = 10.0
        beam_height = 5
        expected_height = beam_height + height_set
        jaws_z = 5.0
        jaws = Component("jaws", setup=PositionAndAngle(0, jaws_z, 90))
        jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        tracking_height = AxisParameter("theta", jaws, ChangeAxis.POSITION)

        tracking_height.sp_no_move = height_set
        tracking_height.move = 1
        result = tracking_height.sp_rbv

        assert_that(result, is_(height_set))
        assert_that(jaws.beam_path_set_point.position_in_mantid_coordinates().y, is_(expected_height))
        assert_that(jaws.beam_path_set_point.position_in_mantid_coordinates().z, is_(close_to(jaws_z, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_component_parameter_in_beam_in_mode_WHEN_parameter_moved_to_THEN_component_is_in_beam(self):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.is_in_beam = False
        sm_in_beam = InBeamParameter("sminbeam", super_mirror)
        in_beam_sp = True

        sm_in_beam.sp_no_move = in_beam_sp
        sm_in_beam.move = 1

        assert_that(sm_in_beam.sp_rbv, is_(in_beam_sp))
        assert_that(super_mirror.beam_path_set_point.is_in_beam, is_(in_beam_sp))

    def test_GIVEN_component_in_beam_parameter_in_mode_WHEN_parameter_moved_to_THEN_component_is_not_in_beam(self):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.is_in_beam = True
        sm_in_beam = InBeamParameter("sminbeam", super_mirror)
        in_beam_sp = False

        sm_in_beam.sp_no_move = in_beam_sp
        sm_in_beam.move = 1

        assert_that(sm_in_beam.sp_rbv, is_(in_beam_sp))
        assert_that(super_mirror.beam_path_set_point.is_in_beam, is_(in_beam_sp))


class TestBeamlineModes(unittest.TestCase):

    def test_GIVEN_unpolarised_mode_and_beamline_parameters_are_set_WHEN_move_THEN_components_move_onto_beam_line(self):
        slit2 = Component("s2", PositionAndAngle(0, z=10, angle=90))
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(0, z=20, angle=90))
        detector = Component("detector", PositionAndAngle(0, z=30, angle=90))
        components = [slit2, ideal_sample_point, detector]

        parameters = [
            AxisParameter("slit2height", slit2, ChangeAxis.POSITION),
            AxisParameter("height", ideal_sample_point, ChangeAxis.POSITION),
            AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE),
            AxisParameter("detectorheight", detector, ChangeAxis.POSITION)]
                      #parameters["detectorAngle": TrackingAngle(detector)
        beam = PositionAndAngle(0, 0, -45)
        beamline = Beamline(components, parameters, [], [DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION], beam)
        beamline.active_mode = DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION.name
        beamline.parameter("theta").sp_no_move = 45
        beamline.parameter("height").sp_no_move = 0
        beamline.parameter("slit2height").sp_no_move = 0
        beamline.parameter("detectorheight").sp_no_move = 0

        beamline.move = 1

        assert_that(slit2.beam_path_set_point.position_in_mantid_coordinates(), is_(position(Position(-10, 10))))
        assert_that(ideal_sample_point.beam_path_set_point.position_in_mantid_coordinates(), is_(position(Position(-20, 20))))
        assert_that(detector.beam_path_set_point.position_in_mantid_coordinates(), is_(position(Position(-10, 30))))

    def test_GIVEN_a_mode_with_a_single_beamline_parameter_in_WHEN_move_THEN_beamline_parameter_is_calculated_on_move(self):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90))
        theta = AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE)
        beamline_mode = BeamlineMode("mode name", [theta.name])
        beamline = Beamline([ideal_sample_point], [theta], [], [beamline_mode])

        theta.sp_no_move = angle_to_set
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        assert_that(ideal_sample_point.beam_path_set_point.get_angular_displacement(), is_(angle_to_set))


    def test_GIVEN_a_mode_with_a_two_beamline_parameter_in_WHEN_move_first_THEN_second_beamline_parameter_is_calculated_and_moved_to(self):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90))
        theta = AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE)
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(y=0, z=10, angle=90))
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)

        beamline_mode = BeamlineMode("mode name", [theta.name, smangle.name])
        beamline = Beamline([super_mirror, ideal_sample_point], [smangle, theta], [], [beamline_mode])
        theta.sp_no_move = angle_to_set
        smangle.sp_no_move = 0
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        smangle_to_set = -10
        smangle.sp = smangle_to_set

        assert_that(ideal_sample_point.beam_path_set_point.get_angular_displacement(), is_(smangle_to_set * 2 + angle_to_set))

    def test_GIVEN_mode_has_initial_parameter_value_WHEN_setting_mode_THEN_component_sp_updated_but_rbv_unchanged(self):
        sm_angle = 0.0
        sm_angle_to_set = 45.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.set_angular_displacement(sm_angle)
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        smangle.sp_no_move = sm_angle
        sp_inits = {smangle.name: sm_angle_to_set}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)
        beamline = Beamline([super_mirror], [smangle], [], [beamline_mode])

        beamline.active_mode = beamline_mode.name

        assert_that(smangle.sp, is_(sm_angle_to_set))
        assert_that(smangle.sp_changed, is_(True))
        assert_that(super_mirror.beam_path_set_point.get_angular_displacement(), is_(sm_angle))

    def test_GIVEN_mode_has_initial_value_for_param_not_in_beamline_WHEN_initialize_mode_THEN_keyerror_raised(self):
        sm_angle = 0.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.set_angular_displacement(sm_angle)
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        smangle.sp_no_move = sm_angle
        sp_inits = {"nonsense name": sm_angle}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)

        with self.assertRaises(BeamlineConfigurationInvalidException):
            Beamline([super_mirror], [smangle], [], [beamline_mode])

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height))

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)

        mode = BeamlineMode("first_param", [sm_angle.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name
        sm_angle.sp_no_move = 10.0

        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height))

    def test_GIVEN_parameter_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = create_parameter_with_initial_value(0, AxisParameter, "smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = create_parameter_with_initial_value(0, AxisParameter, "slit2pos", s2, ChangeAxis.POSITION)

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height))

    def test_GIVEN_parameter_changed_and_not_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(self):
        initial_s2_height = 0.0
        target_s2_height = 1.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        slit2_pos.sp_no_move = target_s2_height
        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(target_s2_height))

    def test_GIVEN_parameter_changed_and_not_in_mode_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
            self):
        initial_s2_height = 0.0
        target_s2_height = 11.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        sm_angle.sp_no_move = 22.5
        slit2_pos.sp_no_move = 1.0
        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(close_to(target_s2_height, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_parameter_changed_and_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
            self):
        initial_s2_height = 0.0
        target_s2_height = 1.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = create_parameter_with_initial_value(0, AxisParameter, "smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = create_parameter_with_initial_value(0, AxisParameter, "slit2pos", s2, ChangeAxis.POSITION)

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        slit2_pos.sp_no_move = target_s2_height
        beamline.move = 1

        assert_that(s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(target_s2_height))

    def test_GIVEN_two_changed_parameters_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_moved_to_SP_RBV(self):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = create_parameter_with_initial_value(True, AxisParameter, "theta", sample_point, ChangeAxis.ANGLE)
        slit4_pos = create_parameter_with_initial_value(0, AxisParameter, "slit4pos", s4, ChangeAxis.POSITION)
        mode = BeamlineMode("both_params", [theta.name, slit4_pos.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.position_in_mantid_coordinates().y, is_(close_to(sample_to_s4_z + s4_height_initial, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_two_changed_parameters_with_second_not_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_unchanged(self):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = AxisParameter("theta", sample_point, ChangeAxis.ANGLE)
        slit4_pos = AxisParameter("slit4pos", s4, ChangeAxis.POSITION)
        mode = BeamlineMode("first_param", [theta.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.position_in_mantid_coordinates().y, is_(s4_height_initial))

    def test_GIVEN_two_changed_parameters_with_first_not_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_unchanged(
            self):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = AxisParameter("theta", sample_point, ChangeAxis.ANGLE)
        slit4_pos = AxisParameter("slit4pos", s4, ChangeAxis.POSITION)
        mode = BeamlineMode("second_params", [slit4_pos.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.position_in_mantid_coordinates().y, is_(s4_height_initial))


class TestBeamlineOnMove(unittest.TestCase):
    def test_GIVEN_three_beamline_parameters_WHEN_move_1st_THEN_all_move(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[0].move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(1, 1, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_WHEN_move_2nd_THEN_2nd_and_3rd_move(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[1].move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(0, 1, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_WHEN_move_3rd_THEN_3rd_moves(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[2].move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(0, 0, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_and_1_and_3_in_mode_WHEN_move_1st_THEN_parameters_in_the_mode_move(self):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()
        beamline.active_mode = "components1and3"

        beamline_parameters[0].move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(1, 0, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_and_3_in_mode_WHEN_move_1st_THEN_only_2nd_parameter_moved(self):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()
        beamline.active_mode = "just2"

        beamline_parameters[0].move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(1, 0, 0), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_in_mode_WHEN_1st_changed_and_move_beamline_THEN_all_move(self):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[0].sp_no_move = 12.0
        beamline.move = 1
        moves = [beamline_parameter.move_component_count for beamline_parameter in beamline_parameters]

        assert_that(moves, contains(1, 1, 1), "beamline parameter move counts")

    @parameterized.expand([("s1", 12.132, "theta", 4.012), ("s3", 1.123, "theta", 2.342)])
    def test_GIVEN_parameter_with_new_sp_WHEN_theta_moved_independently_THEN_parameter_unchanged(self, param, param_sp, theta, theta_sp):
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)

        param_init_position = bl.parameter(param).rbv

        bl.parameter(param).sp_no_move = param_sp
        bl.parameter(theta).sp_no_move = theta_sp
        bl.parameter(theta).move = 1  # Move only theta

        param_final_position = bl.parameter(param).rbv

        assert_that(param_init_position, is_(close_to(param_final_position, delta=1e-6)))

    @parameterized.expand([("s3_gap", 2.452, "theta", 4.012), ("s3_gap", 4.223, "theta", 1.632)])
    def test_GIVEN_slit_gap_parameter_WHEN_theta_moved_independently_THEN_slit_gap_parameter_unchanged(self, param, param_sp, theta, theta_sp):
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_gap_theta_s3_gap_detector(spacing)

        param_init_position = bl.parameter(param).rbv

        bl.parameter(param).sp_no_move = param_sp
        bl.parameter(theta).sp_no_move = theta_sp
        bl.parameter(theta).move = 1  # Move only theta

        param_final_position = bl.parameter(param).rbv

        assert_that(param_final_position, is_(close_to(param_init_position, delta=1e-6)))


class TestBeamlineParameterReadback(unittest.TestCase):

    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_readback_is_changed(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        displacement_parameter = AxisParameter("param", sample, ChangeAxis.POSITION)
        sample.beam_path_rbv.set_displacement(displacement)

        result = displacement_parameter.rbv

        assert_that(result, is_(displacement - beam_height))

    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        displacement_parameter = AxisParameter("param", sample, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.set_displacement(displacement)

        listener.assert_called_once_with(ParameterReadbackUpdate(displacement - beam_height, None, None))

    def test_GIVEN_reflection_angle_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        angle = 3.0
        beam_angle = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        angle_parameter = AxisParameter("param", sample, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.set_angular_displacement(angle)

        listener.assert_called_with(ParameterReadbackUpdate(angle-beam_angle, None, None))

    def test_GIVEN_reflection_angle_on_tilting_component_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = TiltingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        angle = 3.0
        beam_angle = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        angle_parameter = AxisParameter("param", sample, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.set_angular_displacement(angle)

        listener.assert_called_with(ParameterReadbackUpdate(angle-beam_angle, None, None))

    def test_GIVEN_component_in_beam_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        state = True

        displacement_parameter = InBeamParameter("param", sample)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.is_in_beam = state

        listener.assert_called_once_with(ParameterReadbackUpdate(state, None, None))

    def test_GIVEN_theta_WHEN_no_next_component_THEN_value_is_nan(self):

        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 10, 90), angle_to=[])
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 45))
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)

        result = theta.rbv

        assert_that(isnan(result), is_(True), "Should be nan because there is no next component")

    def test_GIVEN_theta_with_45_deg_beam_WHEN_next_component_is_along_beam_THEN_value_is_0(self):

        # Given
        beam_before_and_after_sample = PositionAndAngle(0, 0, 45)

        s3 = Component("s3", setup=PositionAndAngle(20, 20, 135))
        s3.beam_path_rbv.set_incoming_beam(beam_before_and_after_sample)
        s3.beam_path_set_point.set_incoming_beam(beam_before_and_after_sample)

        sample = ThetaComponent("sample", setup=PositionAndAngle(10, 10, 135), angle_to=[s3])
        sample.beam_path_rbv.set_incoming_beam(beam_before_and_after_sample)
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)

        # When
        result = theta.rbv

        # Then
        assert_that(result, is_(0))

    def test_GIVEN_theta_with_0_deg_beam_WHEN_next_component_is_at_45_THEN_value_is_22_5(self):

        height_above_beam = 10
        expected_theta = 22.5
        s3 = Component("s3", setup=PositionAndAngle(height_above_beam, 10, 90))
        s3.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, expected_theta * 2))
        s3.beam_path_set_point.set_position_relative_to_beam(0)

        theta_comp = ThetaComponent("sample", setup=PositionAndAngle(1, 0, 90), angle_to=[s3])
        theta_comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))

        theta = AxisParameter("param", theta_comp, ChangeAxis.ANGLE)

        result = theta.rbv

        assert_that(result, is_(expected_theta))

    def test_GIVEN_position_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(self):
        component = Component("component", setup=PositionAndAngle(0, 10, 90))
        new_displacement = 1.0
        alarm_severity = 1
        alarm_status = 2
        displacement_parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.displacement_update(CorrectedReadbackUpdate(new_displacement, alarm_severity, alarm_status))

        listener.assert_called_once_with(ParameterReadbackUpdate(new_displacement, alarm_severity, alarm_status))
        self.assertEqual(displacement_parameter.alarm_severity, alarm_severity)
        self.assertEqual(displacement_parameter.alarm_status, alarm_status)

    def test_GIVEN_position_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(self):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_displacement = 1.0
        alarm_severity = 1
        alarm_status = 2
        displacement_parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.angle_update(CorrectedReadbackUpdate(new_displacement, alarm_severity, alarm_status))

        listener.assert_called_once_with(ParameterReadbackUpdate(0.0, None, None))
        self.assertEqual(displacement_parameter.alarm_severity, None)
        self.assertEqual(displacement_parameter.alarm_status, None)

    def test_GIVEN_angle_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(self):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        angle_parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.angle_update(CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status))

        listener.assert_called_with(ParameterReadbackUpdate(True, alarm_severity, alarm_status))
        self.assertEqual(angle_parameter.alarm_severity, alarm_severity)
        self.assertEqual(angle_parameter.alarm_status, alarm_status)

    def test_GIVEN_angle_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(self):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        angle_parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.displacement_update(CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status))

        listener.assert_called_with(ParameterReadbackUpdate(0.0, None, None))
        self.assertEqual(angle_parameter.alarm_severity, None)
        self.assertEqual(angle_parameter.alarm_status, None)

    def test_GIVEN_inbeam_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(self):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_value = 1.0
        alarm_severity = 1
        alarm_status = 2
        in_beam_parameter = InBeamParameter("param", component)
        listener = Mock()
        in_beam_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.displacement_update(CorrectedReadbackUpdate(new_value, alarm_severity, alarm_status))

        listener.assert_called_once_with(ParameterReadbackUpdate(True, alarm_severity, alarm_status))
        self.assertEqual(in_beam_parameter.alarm_severity, alarm_severity)
        self.assertEqual(in_beam_parameter.alarm_status, alarm_status)

    def test_GIVEN_angle_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(self):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        in_beam_parameter = InBeamParameter("param", component)
        listener = Mock()
        in_beam_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.angle_update(CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status))

        listener.assert_called_once_with(ParameterReadbackUpdate(True, None, None))
        self.assertEqual(in_beam_parameter.alarm_severity, None)
        self.assertEqual(in_beam_parameter.alarm_status, None)

    def test_GIVEN_direct_parameter_WHEN_updating_value_with_alarm_on_pv_wrapper_THEN_parameter_is_in_alarm_and_propagates_alarm(self):
        pv_wrapper = create_mock_axis("s1vg", 0.0, 1)
        new_value = 1.0
        alarm_severity = 1
        alarm_status = 2
        parameter = DirectParameter("param", pv_wrapper)
        listener = Mock()
        parameter.add_listener(ParameterReadbackUpdate, listener)

        pv_wrapper.trigger_listeners(ReadbackUpdate(new_value, alarm_severity, alarm_status))

        listener.assert_called_once_with(ParameterReadbackUpdate(new_value, alarm_severity, alarm_status))
        self.assertEqual(parameter.alarm_severity, alarm_severity)
        self.assertEqual(parameter.alarm_status, alarm_status)


class TestBeamlineThetaComponentWhenDisabled(unittest.TestCase):

    def test_GIVEN_theta_with_0_deg_beam_and_next_component_in_beam_but_disabled_WHEN_set_theta_to_45_THEN_component_sp_is_at_45_degrees(self):

        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90), angle_to=[detector])
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result = detector.beam_path_set_point.get_position_relative_to_beam()

        assert_that(result, is_(close_to(-10.0, 1e-6)))  # the beam is now above the current position. The beam line parameter needs to be triggered to make is move

    def test_GIVEN_theta_with_0_deg_beam_and_next_component_in_beam_is_not_disabled_WHEN_set_theta_to_45_THEN_component_sp_is_not_altered(self):
        # this calculation will be done via the beamline not the forced copy of output beam
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90), angle_to=[detector])
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(True)

        theta.sp = 22.5
        result = detector.beam_path_set_point.get_position_relative_to_beam()

        assert_that(result, is_(close_to(0, 1e-6)))

    def test_GIVEN_theta_with_0_deg_beam_and_next_two_component_in_beam_and_are_disabled_WHEN_set_theta_to_45_THEN_first_component_altered_second_one_not(self):
        # this calculation will be done via the beamline not the forced copy of output beam
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        detector2 = Component("detector", setup=PositionAndAngle(0, 20, 90))
        detector2.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90), angle_to=[detector, detector2])
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)
        detector2.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result1 = detector.beam_path_set_point.get_position_relative_to_beam()
        result2 = detector2.beam_path_set_point.get_position_relative_to_beam()

        assert_that(result1, is_(close_to(-10, 1e-6)))
        assert_that(result2, is_(close_to(0, 1e-6)))

    def test_GIVEN_theta_with_0_deg_beam_and_next_first_component_out_of_beam_second_in_beam_and_are_disabled_WHEN_set_theta_to_45_THEN_first_component_not_altered_second_one_is(self):
        # this calculation will be done via the beamline not the forced copy of output beam
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        detector2 = Component("detector", setup=PositionAndAngle(0, 20, 90))
        detector2.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90), angle_to=[detector, detector2])
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)
        detector.beam_path_set_point.is_in_beam = False
        detector2.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result1 = detector.beam_path_set_point.get_position_relative_to_beam()
        result2 = detector2.beam_path_set_point.get_position_relative_to_beam()

        assert_that(result1, is_(close_to(0, 1e-6)))
        assert_that(result2, is_(close_to(-20, 1e-6)))


class TestInitSetpoints(unittest.TestCase):

    def setUp(self):
        setup_autosave({"param_float": 0.1}, {"param_bool": True})
        self.component = Component("component", setup=PositionAndAngle(0, 1, 90))
        self.angle_component = TiltingComponent("angle_component", setup=PositionAndAngle(0, 10, 90))
        self.jaws = create_mock_axis("s1vg", 0.2, 1)

    def test_GIVEN_autosave_is_not_set_WHEN_creating_param_THEN_defaults_to_false(self):
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION)
        self.assertFalse(param._autosave)

    def test_GIVEN_autosave_is_false_THEN_parameter_sp_is_none(self):
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=False)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_autosave_value(self):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_none(self):
        param_name = "param_not_in_file"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_none(self):
        param_name = "param_bool"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_angle_parameter_THEN_sp_is_autosave_value(self):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_angle_parameter_THEN_sp_is_none(self):
        param_name = "param_not_in_file"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_angle_parameter_THEN_sp_is_none(self):
        param_name = "param_bool"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_in_beam_parameter_THEN_sp_is_autosave_value(self):
        expected = True
        param_name = "param_bool"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_in_beam_parameter_THEN_sp_is_none(self):
        param_name = "param_not_in_file"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_in_beam_parameter_THEN_sp_is_none(self):
        param_name = "param_float"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_direct_parameter_THEN_sp_is_autosave_value(self):
        expected = 0.1
        param_name = "param_float"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_direct_parameter_THEN_sp_is_taken_from_motor_instead(self):
        expected = 0.2
        param_name = "param_not_in_file"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_direct_parameter_THEN_sp_is_taken_from_motor_instead(self):
        expected = 0.2
        param_name = "param_bool"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_WHEN_initialising_tracking_position_THEN_beam_calc_caches_autosaved_offset(self):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)
        actual = self.component.beam_path_set_point.autosaved_offset

        self.assertEqual(expected, actual)

    def test_GIVEN_autosave_is_false_WHEN_initialising_tracking_position_THEN_beam_calc_has_no_autosaved_offset(self):
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=False)
        actual = self.component.beam_path_set_point.autosaved_offset

        self.assertIsNone(actual)


if __name__ == '__main__':
    unittest.main()
