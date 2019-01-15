import unittest
from math import isnan

from hamcrest import *
from mock import Mock

from ReflectometryServer.beamline import Beamline, BeamlineMode

from ReflectometryServer.components import ReflectingComponent, Component, ThetaComponent
from ReflectometryServer.geometry import Position, PositionAndAngle
from ReflectometryServer.parameters import AngleParameter, TrackingPosition, ComponentEnabled, SlitGapParameter
from data_mother import DataMother, EmptyBeamlineParameter
from server_common.channel_access import AlarmSeverity, AlarmStatus
from utils import position, DEFAULT_TEST_TOLERANCE


class TestBeamlineParameter(unittest.TestCase):

    def test_GIVEN_theta_WHEN_set_set_point_THEN_sample_hasnt_moved(self):
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        mirror_pos = -100
        sample.beam_path_set_point.angle = mirror_pos
        theta = AngleParameter("theta", sample)

        theta.sp_no_move = theta_set

        assert_that(theta.sp, is_(theta_set))
        assert_that(sample.beam_path_set_point.angle, is_(mirror_pos))

    def test_GIVEN_theta_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_sample_is_at_setpoint_postion(self):

        theta_set = 10.0
        expected_sample_angle = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.angle = mirror_pos
        theta = AngleParameter("theta", sample)

        theta.sp_no_move = theta_set
        theta.move = 1
        result = theta.sp_rbv

        assert_that(result, is_(theta_set))
        assert_that(sample.beam_path_set_point.angle, is_(expected_sample_angle))

    def test_GIVEN_theta_set_WHEN_set_point_set_and_move_THEN_readback_is_as_original_value_but_setpoint_is_new_value(self):

        original_theta = 1.0
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.angle = mirror_pos
        theta = AngleParameter("theta", sample)
        theta.sp = original_theta

        theta.sp_no_move = theta_set
        result = theta.sp_rbv

        assert_that(result, is_(original_theta))
        assert_that(theta.sp, is_(theta_set))

    def test_GIVEN_theta_and_a_set_but_no_move_WHEN_get_changed_THEN_changed_is_true(self):

        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AngleParameter("theta", sample)

        theta.sp_no_move = theta_set
        result = theta.sp_changed

        assert_that(result, is_(True))

    def test_GIVEN_theta_and_a_set_and_move_WHEN_get_changed_THEN_changed_is_false(self):

        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AngleParameter("theta", sample)

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
        sample.beam_path_set_point.angle = mirror_pos
        reflection_angle = AngleParameter("theta", sample)

        reflection_angle.sp_no_move = angle_set
        reflection_angle.move = 1
        result = reflection_angle.sp_rbv

        assert_that(result, is_(angle_set))
        assert_that(sample.beam_path_set_point.angle, is_(expected_sample_angle))

    def test_GIVEN_jaw_height_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_jaws_are_at_setpoint_postion(self):

        height_set = 10.0
        beam_height = 5
        expected_height = beam_height + height_set
        jaws_z = 5.0
        jaws = Component("jaws", setup=PositionAndAngle(0, jaws_z, 90))
        jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        tracking_height = TrackingPosition("theta", jaws)

        tracking_height.sp_no_move = height_set
        tracking_height.move = 1
        result = tracking_height.sp_rbv

        assert_that(result, is_(height_set))
        assert_that(jaws.beam_path_set_point.sp_position().y, is_(expected_height))
        assert_that(jaws.beam_path_set_point.sp_position().z, is_(close_to(jaws_z, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_component_parameter_enabled_in_mode_WHEN_parameter_moved_to_THEN_component_is_enabled(self):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.enabled = False
        sm_enabled = ComponentEnabled("smenabled", super_mirror)
        enabled_sp = True

        sm_enabled.sp_no_move = enabled_sp
        sm_enabled.move = 1

        assert_that(sm_enabled.sp_rbv, is_(enabled_sp))
        assert_that(super_mirror.beam_path_set_point.enabled, is_(enabled_sp))

    def test_GIVEN_component_parameter_disabled_in_mode_WHEN_parameter_moved_to_THEN_component_is_disabled(self):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.enabled = True
        sm_enabled = ComponentEnabled("smenabled", super_mirror)
        enabled_sp = False

        sm_enabled.sp_no_move = enabled_sp
        sm_enabled.move = 1

        assert_that(sm_enabled.sp_rbv, is_(enabled_sp))
        assert_that(super_mirror.beam_path_set_point.enabled, is_(enabled_sp))

class TestBeamlineModes(unittest.TestCase):

    def test_GIVEN_unpolarised_mode_and_beamline_parameters_are_set_WHEN_move_THEN_components_move_onto_beam_line(self):
        slit2 = Component("s2", PositionAndAngle(0, z=10, angle=90))
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(0, z=20, angle=90))
        detector = Component("detector", PositionAndAngle(0, z=30, angle=90))
        components = [slit2, ideal_sample_point, detector]

        parameters = [
            TrackingPosition("slit2height", slit2),
            TrackingPosition("height", ideal_sample_point),
            AngleParameter("theta", ideal_sample_point),
            TrackingPosition("detectorheight", detector)]
                      #parameters["detectorAngle": TrackingAngle(detector)
        beam = PositionAndAngle(0, 0, -45)
        beamline = Beamline(components, parameters, [], [DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION], beam)
        beamline.active_mode = DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION.name
        beamline.parameter("theta").sp_no_move = 45
        beamline.parameter("height").sp_no_move = 0
        beamline.parameter("slit2height").sp_no_move = 0
        beamline.parameter("detectorheight").sp_no_move = 0

        beamline.move = 1

        assert_that(slit2.beam_path_set_point.sp_position(), is_(position(Position(-10, 10))))
        assert_that(ideal_sample_point.beam_path_set_point.sp_position(), is_(position(Position(-20, 20))))
        assert_that(detector.beam_path_set_point.sp_position(), is_(position(Position(-10, 30))))

    def test_GIVEN_a_mode_with_a_single_beamline_parameter_in_WHEN_move_THEN_beamline_parameter_is_calculated_on_move(self):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90))
        theta = AngleParameter("theta", ideal_sample_point)
        beamline_mode = BeamlineMode("mode name", [theta.name])
        beamline = Beamline([ideal_sample_point], [theta], [], [beamline_mode])

        theta.sp_no_move = angle_to_set
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        assert_that(ideal_sample_point.beam_path_set_point.angle, is_(angle_to_set))


    def test_GIVEN_a_mode_with_a_two_beamline_parameter_in_WHEN_move_first_THEN_second_beamline_parameter_is_calculated_and_moved_to(self):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent("ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90))
        theta = AngleParameter("theta", ideal_sample_point)
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(y=0, z=10, angle=90))
        smangle = AngleParameter("smangle", super_mirror)

        beamline_mode = BeamlineMode("mode name", [theta.name, smangle.name])
        beamline = Beamline([super_mirror, ideal_sample_point], [smangle, theta], [], [beamline_mode])
        theta.sp_no_move = angle_to_set
        smangle.sp_no_move = 0
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        smangle_to_set = -10
        smangle.sp = smangle_to_set

        assert_that(ideal_sample_point.beam_path_set_point.angle, is_(smangle_to_set*2 + angle_to_set))

    def test_GIVEN_mode_has_initial_parameter_value_WHEN_setting_mode_THEN_component_sp_updated_but_rbv_unchanged(self):
        sm_angle = 0.0
        sm_angle_to_set = 45.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.angle = sm_angle
        smangle = AngleParameter("smangle", super_mirror)
        smangle.sp_no_move = sm_angle
        sp_inits = {smangle.name: sm_angle_to_set}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)
        beamline = Beamline([super_mirror], [smangle], [], [beamline_mode])

        beamline.active_mode = beamline_mode.name

        assert_that(smangle.sp, is_(sm_angle_to_set))
        assert_that(smangle.sp_changed, is_(True))
        assert_that(super_mirror.beam_path_set_point.angle, is_(sm_angle))

    def test_GIVEN_mode_has_initial_value_for_param_not_in_beamline_WHEN_initialize_mode_THEN_keyerror_raised(self):
        sm_angle = 0.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.angle = sm_angle
        smangle = AngleParameter("smangle", super_mirror)
        smangle.sp_no_move = sm_angle
        sp_inits = {"nonsense name": sm_angle}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)

        with self.assertRaises(KeyError):
            Beamline([super_mirror], [smangle], [], [beamline_mode])

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror)
        slit2_pos = TrackingPosition("slit2pos", s2)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(initial_s2_height))

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror)
        slit2_pos = TrackingPosition("slit2pos", s2)

        mode = BeamlineMode("first_param", [sm_angle.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name
        sm_angle.sp_no_move = 10.0

        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(initial_s2_height))

    def test_GIVEN_parameter_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(self):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror, True)
        slit2_pos = TrackingPosition("slit2pos", s2, True)

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(initial_s2_height))

    def test_GIVEN_parameter_changed_and_not_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(self):
        initial_s2_height = 0.0
        target_s2_height = 1.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror)
        slit2_pos = TrackingPosition("slit2pos", s2)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        slit2_pos.sp_no_move = target_s2_height
        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(target_s2_height))

    def test_GIVEN_parameter_changed_and_not_in_mode_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
            self):
        initial_s2_height = 0.0
        target_s2_height = 11.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror)
        slit2_pos = TrackingPosition("slit2pos", s2)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        sm_angle.sp_no_move = 22.5
        slit2_pos.sp_no_move = 1.0
        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(close_to(target_s2_height, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_parameter_changed_and_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
            self):
        initial_s2_height = 0.0
        target_s2_height = 1.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AngleParameter("smangle", super_mirror, True)
        slit2_pos = TrackingPosition("slit2pos", s2, True)

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        slit2_pos.sp_no_move = target_s2_height
        beamline.move = 1

        assert_that(s2.beam_path_set_point.sp_position().y, is_(target_s2_height))

    def test_GIVEN_two_changed_parameters_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_moved_to_SP_RBV(self):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = AngleParameter("theta", sample_point, True)
        slit4_pos = TrackingPosition("slit4pos", s4, True)
        mode = BeamlineMode("both_params", [theta.name, slit4_pos.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.sp_position().y, is_(close_to(sample_to_s4_z + s4_height_initial, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_two_changed_parameters_with_second_not_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_unchanged(self):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = AngleParameter("theta", sample_point, True)
        slit4_pos = TrackingPosition("slit4pos", s4, True)
        mode = BeamlineMode("first_param", [theta.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.sp_position().y, is_(s4_height_initial))

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
        theta = AngleParameter("theta", sample_point, True)
        slit4_pos = TrackingPosition("slit4pos", s4, True)
        mode = BeamlineMode("second_params", [slit4_pos.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(s4.beam_path_set_point.sp_position().y, is_(s4_height_initial))


class TestBeamlineOnMove(unittest.TestCase):

    def test_GIVEN_two_beamline_parameters_with_same_name_WHEN_construct_THEN_error(self):
        one = EmptyBeamlineParameter("same")
        two = EmptyBeamlineParameter("same")

        assert_that(calling(Beamline).with_args([], [one, two], [], []), raises(ValueError))

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


class TestBeamlineParameterReadback(unittest.TestCase):

    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_readback_is_changed(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        beamline_position = TrackingPosition("param", sample)
        sample.beam_path_rbv.set_displacement(displacement, AlarmSeverity.No, AlarmStatus.No)

        result = beamline_position.rbv

        assert_that(result, is_(displacement - beam_height))

    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        beamline_position = TrackingPosition("param", sample)
        listener = Mock()
        beamline_position.add_rbv_change_listener(listener)
        sample.beam_path_rbv.set_displacement(displacement, AlarmSeverity.No, AlarmStatus.No)

        listener.assert_called_once_with(displacement - beam_height)

    def test_GIVEN_reflection_angle_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        angle = 3.0
        beam_angle = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        beamline_position = AngleParameter("param", sample)
        listener = Mock()
        beamline_position.add_rbv_change_listener(listener)
        sample.beam_path_rbv.angle = angle

        listener.assert_called_once_with(angle-beam_angle)

    def test_GIVEN_component_enabled_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(self):

        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        state = True

        beamline_position = ComponentEnabled("param", sample)
        listener = Mock()
        beamline_position.add_rbv_change_listener(listener)
        sample.beam_path_rbv.enabled = state

        listener.assert_called_once_with(state)

    def test_GIVEN_theta_WHEN_no_next_component_THEN_value_is_nan(self):

        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 10, 90), angle_to=[])
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 45))
        theta = AngleParameter("param", sample)

        result = theta.rbv

        assert_that(isnan(result), is_(True), "Should be nan because there is no next component")

    def test_GIVEN_theta_with_45_deg_beam_WHEN_next_component_is_along_beam_THEN_value_is_0(self):

        s3 = Component("s3", setup=PositionAndAngle(20, 20, 135))
        s3.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 45))
        sample = ThetaComponent("sample", setup=PositionAndAngle(10, 10, 135), angle_to=[s3])
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 45))
        theta = AngleParameter("param", sample)

        result = theta.rbv

        assert_that(result, is_(0))

    def test_GIVEN_theta_with_0_deg_beam_WHEN_next_component_is_at_45_THEN_value_is_22_5(self):

        s3 = Component("s3", setup=PositionAndAngle(10, 10, 90))
        sample = ThetaComponent("sample", setup=PositionAndAngle(10, 0, 90), angle_to=[s3])
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))
        theta = AngleParameter("param", sample)

        result = theta.rbv

        assert_that(result, is_(45/2.0))


if __name__ == '__main__':
    unittest.main()
