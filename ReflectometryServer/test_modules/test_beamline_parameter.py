import unittest
from math import isnan
from time import sleep

from hamcrest import *
from mock import Mock, patch
from parameterized import parameterized

from ReflectometryServer import *
from ReflectometryServer import ChangeAxis
from ReflectometryServer.beamline import BeamlineConfigurationInvalidException
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.parameters import ParameterReadbackUpdate
from ReflectometryServer.pv_wrapper import ReadbackUpdate
from ReflectometryServer.server_status_manager import STATUS_MANAGER
from ReflectometryServer.test_modules.data_mother import DataMother, create_mock_axis
from ReflectometryServer.test_modules.utils import (
    DEFAULT_TEST_TOLERANCE,
    create_parameter_with_initial_value,
    position,
    setup_autosave,
)


class TestBeamlineParameter(unittest.TestCase):
    def test_GIVEN_theta_WHEN_set_set_point_THEN_sample_hasnt_moved(self):
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        mirror_pos = -100
        sample.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(mirror_pos, None, None)
        )
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set

        assert_that(theta.sp, is_(theta_set))
        assert_that(
            sample.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(), is_(mirror_pos)
        )

    def test_GIVEN_theta_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_sample_is_at_setpoint_postion(
        self,
    ):
        theta_set = 10.0
        expected_sample_angle = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(mirror_pos, None, None)
        )
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.sp_no_move = theta_set
        theta.move = 1
        result = theta.sp_rbv
        assert_that(result, is_(theta_set))
        assert_that(
            sample.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(),
            is_(expected_sample_angle),
        )

    def test_GIVEN_theta_set_WHEN_set_point_set_and_move_THEN_readback_is_as_original_value_but_setpoint_is_new_value(
        self,
    ):
        original_theta = 1.0
        theta_set = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(mirror_pos, None, None)
        )
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

    def test_GIVEN_reflection_angle_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_sample_is_at_setpoint_postion(
        self,
    ):
        angle_set = 10.0
        expected_sample_angle = 10.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        mirror_pos = -100
        sample.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(mirror_pos, None, None)
        )
        reflection_angle = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        reflection_angle.sp_no_move = angle_set
        reflection_angle.move = 1
        result = reflection_angle.sp_rbv

        assert_that(result, is_(angle_set))
        assert_that(
            sample.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(),
            is_(expected_sample_angle),
        )

    def test_GIVEN_jaw_height_WHEN_set_set_point_and_move_THEN_readback_is_as_set_and_jaws_are_at_setpoint_postion(
        self,
    ):
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
        assert_that(
            jaws.beam_path_set_point.position_in_mantid_coordinates().y, is_(expected_height)
        )
        assert_that(
            jaws.beam_path_set_point.position_in_mantid_coordinates().z,
            is_(close_to(jaws_z, DEFAULT_TEST_TOLERANCE)),
        )

    def test_GIVEN_component_parameter_in_beam_in_mode_WHEN_parameter_moved_to_THEN_component_is_in_beam(
        self,
    ):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.is_in_beam = False
        sm_in_beam = InBeamParameter("sminbeam", super_mirror)
        in_beam_sp = True

        sm_in_beam.sp_no_move = in_beam_sp
        sm_in_beam.move = 1

        assert_that(sm_in_beam.sp_rbv, is_(in_beam_sp))
        assert_that(super_mirror.beam_path_set_point.is_in_beam, is_(in_beam_sp))

    def test_GIVEN_component_in_beam_parameter_in_mode_WHEN_parameter_moved_to_THEN_component_is_not_in_beam(
        self,
    ):
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.axis[ChangeAxis.POSITION].park_sequence_count = 1
        super_mirror.beam_path_set_point.axis[ChangeAxis.POSITION].is_in_beam = True
        sm_in_beam = InBeamParameter("sminbeam", super_mirror)
        in_beam_sp = False

        sm_in_beam.sp_no_move = in_beam_sp
        sm_in_beam.move = 1

        assert_that(sm_in_beam.sp_rbv, is_(in_beam_sp))
        assert_that(super_mirror.beam_path_set_point.is_in_beam, is_(in_beam_sp))

    def test_GIVEN_parameter_WHEN_setting_define_position_sp_THEN_define_as_changed_flag_is_false(
        self,
    ):
        parameter = 6.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.define_current_value_as.new_value_sp_rbv = parameter
        result = theta.define_current_value_as.changed

        assert_that(result, is_(False))

    def test_GIVEN_parameter_WHEN_setting_define_position_sp_no_action_THEN_define_as_sp_rbv_is_unchanged(
        self,
    ):
        parameter = 6.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        initial = theta.define_current_value_as.new_value_sp
        theta.define_current_value_as.new_value_sp = parameter
        result = theta.define_current_value_as.new_value_sp_rbv

        assert_that(result, is_(initial))
        assert_that(result, is_not(parameter))

    def test_GIVEN_parameter_WHEN_setting_define_position_sp_no_action_THEN_define_as_changed_flag_is_true(
        self,
    ):
        parameter = 6.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.define_current_value_as.new_value_sp = parameter
        result = theta.define_current_value_as.changed

        assert_that(result, is_(True))

    def test_GIVEN_define_as_sp_set_on_parameter_WHEN_triggering_define_as_action_THEN_define_as_sp_rbv_is_updated(
        self,
    ):
        parameter = 6.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.define_current_value_as.new_value_sp = parameter
        theta.define_current_value_as.do_action()
        result = theta.define_current_value_as.new_value_sp_rbv

        assert_that(result, is_(parameter))

    def test_GIVEN_define_as_sp_set_on_parameter_WHEN_triggering_define_as_action_THEN_define_as_changed_flag_is_false(
        self,
    ):
        parameter = 6.0
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        theta = AxisParameter("theta", sample, ChangeAxis.ANGLE)

        theta.define_current_value_as.new_value_sp = parameter
        theta.define_current_value_as.do_action()
        result = theta.define_current_value_as.changed

        assert_that(result, is_(False))

    @parameterized.expand([ChangeAxis.DISPLACEMENT_POSITION, ChangeAxis.DISPLACEMENT_ANGLE])
    def test_GIVEN_beam_out_parameter_WHEN_setting_sp_THEN_sp_ignored(self, change_axis):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        beam_out_y = AxisParameter("beam_out_y", sample, change_axis)
        expected = None

        beam_out_y.sp = 5
        actual = beam_out_y.sp

        assert_that(actual, is_(expected))

    @parameterized.expand([ChangeAxis.DISPLACEMENT_POSITION, ChangeAxis.DISPLACEMENT_ANGLE])
    def test_GIVEN_read_only_parameter_WHEN_setting_sp_no_action_THEN_sp_not_set(self, change_axis):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))
        beam_out_y = AxisParameter("beam_out_y", sample, change_axis)
        expected = None

        beam_out_y.sp_no_move = 5
        actual = beam_out_y.sp

        assert_that(actual, is_(expected))

    def test_GIVEN_read_only_parameter_WHEN_param_has_mode_inits_THEN_inits_ignored(self):
        expected = 0.0
        param_init_to_ignore = 5.0
        sample_comp = ReflectingComponent("sample", setup=PositionAndAngle(0, 0, 90))

        disp_angle = AxisParameter("disp_height", sample_comp, ChangeAxis.DISPLACEMENT_ANGLE)
        sp_inits = {disp_angle.name: param_init_to_ignore}
        beamline_mode = BeamlineMode("mode name", [disp_angle.name], sp_inits)
        beamline = Beamline([sample_comp], [disp_angle], [], [beamline_mode])

        beamline.active_mode = beamline_mode.name

        assert_that(disp_angle.sp, is_(expected))
        assert_that(disp_angle.sp_changed, is_(False))
        assert_that(
            sample_comp.beam_path_set_point.axis[ChangeAxis.DISPLACEMENT_ANGLE].get_displacement(),
            is_(expected),
        )


class TestBeamlineParametersThoseRBVMirrosSP(unittest.TestCase):
    def test_GIVEN_axis_parameter_has_sp_mirros_rbv_WHEN_move_THEN_sp_is_moved_to_rbv(self):
        expected_sp = 1.0
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        param = AxisParameter("param", comp, axis=ChangeAxis.POSITION, sp_mirrors_rbv=True)
        param.sp = 0

        comp.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(expected_sp, None, None)
        )
        param.move_to_sp_no_callback()  # as beamline does

        assert_that(param.sp, is_(expected_sp))

    def test_GIVEN_parameter_has_sp_mirros_rbv_WHEN_in_beam_THEN_parameter_is_disabled(self):
        expected_is_disabled = True
        comp = Component("comp", PositionAndAngle(0, 0, 90))
        comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))
        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        param = AxisParameter("param", comp, axis=ChangeAxis.POSITION, sp_mirrors_rbv=True)
        param_in = InBeamParameter("inbeam", comp)
        param_in.sp = True
        param.sp = 0

        assert_that(param.is_disabled, is_(expected_is_disabled))


class TestBeamlineModes(unittest.TestCase):
    def test_GIVEN_unpolarised_mode_and_beamline_parameters_are_set_WHEN_move_THEN_components_move_onto_beam_line(
        self,
    ):
        slit2 = Component("s2", PositionAndAngle(0, z=10, angle=90))
        ideal_sample_point = ReflectingComponent(
            "ideal_sample_point", PositionAndAngle(0, z=20, angle=90)
        )
        detector = Component("detector", PositionAndAngle(0, z=30, angle=90))
        components = [slit2, ideal_sample_point, detector]

        parameters = [
            AxisParameter("slit2height", slit2, ChangeAxis.POSITION),
            AxisParameter("height", ideal_sample_point, ChangeAxis.POSITION),
            AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE),
            AxisParameter("detectorheight", detector, ChangeAxis.POSITION),
        ]
        # parameters["detectorAngle": TrackingAngle(detector)
        beam = PositionAndAngle(0, 0, -45)
        beamline = Beamline(
            components, parameters, [], [DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION], beam
        )
        beamline.active_mode = DataMother.BEAMLINE_MODE_NEUTRON_REFLECTION.name
        beamline.parameter("theta").sp_no_move = 45
        beamline.parameter("height").sp_no_move = 0
        beamline.parameter("slit2height").sp_no_move = 0
        beamline.parameter("detectorheight").sp_no_move = 0

        beamline.move = 1

        assert_that(
            slit2.beam_path_set_point.position_in_mantid_coordinates(),
            is_(position(Position(-10, 10))),
        )
        assert_that(
            ideal_sample_point.beam_path_set_point.position_in_mantid_coordinates(),
            is_(position(Position(-20, 20))),
        )
        assert_that(
            detector.beam_path_set_point.position_in_mantid_coordinates(),
            is_(position(Position(-10, 30))),
        )

    def test_GIVEN_a_mode_with_a_single_beamline_parameter_in_WHEN_move_THEN_beamline_parameter_is_calculated_on_move(
        self,
    ):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent(
            "ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90)
        )
        theta = AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE)
        beamline_mode = BeamlineMode("mode name", [theta.name])
        beamline = Beamline([ideal_sample_point], [theta], [], [beamline_mode])

        theta.sp_no_move = angle_to_set
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        assert_that(
            ideal_sample_point.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(),
            is_(angle_to_set),
        )

    def test_GIVEN_a_mode_with_a_two_beamline_parameter_in_WHEN_move_first_THEN_second_beamline_parameter_is_calculated_and_moved_to(
        self,
    ):
        angle_to_set = 45.0
        ideal_sample_point = ReflectingComponent(
            "ideal_sample_point", PositionAndAngle(y=0, z=20, angle=90)
        )
        theta = AxisParameter("theta", ideal_sample_point, ChangeAxis.ANGLE)
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(y=0, z=10, angle=90))
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)

        beamline_mode = BeamlineMode("mode name", [theta.name, smangle.name])
        beamline = Beamline(
            [super_mirror, ideal_sample_point], [smangle, theta], [], [beamline_mode]
        )
        theta.sp_no_move = angle_to_set
        smangle.sp_no_move = 0
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        smangle_to_set = -10
        smangle.sp = smangle_to_set

        assert_that(
            ideal_sample_point.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(),
            is_(smangle_to_set * 2 + angle_to_set),
        )

    def test_GIVEN_virtual_parmeter_without_component_WHEN_moved_THEN_sp_updated_and_rbv_updated(
        self,
    ):
        setpoint = 10
        parameter = VirtualParameter("virtual", ChangeAxis.HEIGHT)

        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        beamline_mode = BeamlineMode("mode name", [parameter.name])
        beamline = Beamline([super_mirror], [parameter], [], [beamline_mode])
        parameter.sp_no_move = setpoint
        beamline.active_mode = beamline_mode.name
        beamline.move = 1

        self.assertEqual(parameter.sp_no_move, parameter.sp)
        self.assertEqual(parameter.sp_no_move, parameter.sp_rbv)

    def test_GIVEN_mode_has_initial_parameter_value_WHEN_setting_mode_THEN_component_sp_updated_but_rbv_unchanged(
        self,
    ):
        sm_angle = 0.0
        sm_angle_to_set = 45.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(sm_angle, None, None)
        )
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        smangle.sp_no_move = sm_angle
        sp_inits = {smangle.name: sm_angle_to_set}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)
        beamline = Beamline([super_mirror], [smangle], [], [beamline_mode])

        beamline.active_mode = beamline_mode.name

        assert_that(smangle.sp, is_(sm_angle_to_set))
        assert_that(smangle.sp_changed, is_(True))
        assert_that(
            super_mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].get_displacement(),
            is_(sm_angle),
        )

    def test_GIVEN_mode_has_initial_value_for_param_not_in_beamline_WHEN_initialize_mode_THEN_keyerror_raised(
        self,
    ):
        sm_angle = 0.0
        super_mirror = ReflectingComponent("super mirror", PositionAndAngle(z=10, y=0, angle=90))
        super_mirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(sm_angle, None, None)
        )
        smangle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        smangle.sp_no_move = sm_angle
        sp_inits = {"nonsense name": sm_angle}
        beamline_mode = BeamlineMode("mode name", [smangle.name], sp_inits)

        with self.assertRaises(BeamlineConfigurationInvalidException):
            Beamline([super_mirror], [smangle], [], [beamline_mode])

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(
        self,
    ):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = AxisParameter("smangle", super_mirror, ChangeAxis.ANGLE)
        slit2_pos = AxisParameter("slit2pos", s2, ChangeAxis.POSITION)

        empty_mode = BeamlineMode("empty", [])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [empty_mode])
        beamline.active_mode = empty_mode.name

        beamline.move = 1

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height)
        )

    def test_GIVEN_parameter_not_in_mode_and_not_changed_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(
        self,
    ):
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

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height)
        )

    def test_GIVEN_parameter_in_mode_and_not_changed_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_unchanged(
        self,
    ):
        initial_s2_height = 0.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = create_parameter_with_initial_value(
            0, AxisParameter, "smangle", super_mirror, ChangeAxis.ANGLE
        )
        slit2_pos = create_parameter_with_initial_value(
            0, AxisParameter, "slit2pos", s2, ChangeAxis.POSITION
        )

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        beamline.move = 1

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(initial_s2_height)
        )

    def test_GIVEN_parameter_changed_and_not_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
        self,
    ):
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

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(target_s2_height)
        )

    def test_GIVEN_parameter_changed_and_not_in_mode_and_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
        self,
    ):
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

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y,
            is_(close_to(target_s2_height, DEFAULT_TEST_TOLERANCE)),
        )

    def test_GIVEN_parameter_changed_and_in_mode_and_no_previous_parameter_changed_WHEN_moving_beamline_THEN_parameter_moved_to_sp(
        self,
    ):
        initial_s2_height = 0.0
        target_s2_height = 1.0
        super_mirror = ReflectingComponent("sm", PositionAndAngle(0.0, 10, 90.0))
        s2 = Component("s2", PositionAndAngle(initial_s2_height, 20, 90.0))

        sm_angle = create_parameter_with_initial_value(
            0, AxisParameter, "smangle", super_mirror, ChangeAxis.ANGLE
        )
        slit2_pos = create_parameter_with_initial_value(
            0, AxisParameter, "slit2pos", s2, ChangeAxis.POSITION
        )

        mode = BeamlineMode("both_params", [sm_angle.name, slit2_pos.name])

        beamline = Beamline([super_mirror, s2], [sm_angle, slit2_pos], [], [mode])
        beamline.active_mode = mode.name

        slit2_pos.sp_no_move = target_s2_height
        beamline.move = 1

        assert_that(
            s2.beam_path_set_point.position_in_mantid_coordinates().y, is_(target_s2_height)
        )

    def test_GIVEN_two_changed_parameters_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_moved_to_SP_RBV(
        self,
    ):
        beam_start = PositionAndAngle(0, 0, 0)
        s4_height_initial = 0.0
        s4_height_sp = 1.0
        bounced_beam_angle = 45.0
        sample_z = 10.0
        sample_to_s4_z = 10.0
        sample_point = ReflectingComponent("sm", PositionAndAngle(0, sample_z, 90))
        s4 = Component("s4", PositionAndAngle(s4_height_initial, sample_z + sample_to_s4_z, 90))
        theta = create_parameter_with_initial_value(
            True, AxisParameter, "theta", sample_point, ChangeAxis.ANGLE
        )
        slit4_pos = create_parameter_with_initial_value(
            0, AxisParameter, "slit4pos", s4, ChangeAxis.POSITION
        )
        mode = BeamlineMode("both_params", [theta.name, slit4_pos.name])
        beamline = Beamline([sample_point, s4], [theta, slit4_pos], [], [mode])
        beamline.active_mode = mode.name

        theta.sp_no_move = bounced_beam_angle / 2
        slit4_pos.sp_no_move = s4_height_sp
        theta.move = 1

        assert_that(
            s4.beam_path_set_point.position_in_mantid_coordinates().y,
            is_(close_to(sample_to_s4_z + s4_height_initial, DEFAULT_TEST_TOLERANCE)),
        )

    def test_GIVEN_two_changed_parameters_with_second_not_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_unchanged(
        self,
    ):
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

        assert_that(
            s4.beam_path_set_point.position_in_mantid_coordinates().y, is_(s4_height_initial)
        )

    def test_GIVEN_two_changed_parameters_with_first_not_in_mode_WHEN_first_parameter_moved_to_SP_THEN_second_parameter_unchanged(
        self,
    ):
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

        assert_that(
            s4.beam_path_set_point.position_in_mantid_coordinates().y, is_(s4_height_initial)
        )

    def test_GIVEN_component_in_beam_sp_rbv_is_out_for_setpoint_beam_path_THEN_axis_param_is_disabled(
        self,
    ):
        in_beam = False
        expected = True
        component = Component("test_comp", setup=PositionAndAngle(0, 0, 90))
        param = AxisParameter("param", component, ChangeAxis.POSITION)

        component.beam_path_set_point.is_in_beam = in_beam
        actual = param.is_disabled

        assert_that(actual, is_(expected))

    def test_GIVEN_component_in_beam_sp_rbv_is_in_for_setpoint_beam_path_THEN_axis_param_is_not_disabled(
        self,
    ):
        in_beam = True
        expected = False
        component = Component("test_comp", setup=PositionAndAngle(0, 0, 90))
        param = AxisParameter("param", component, ChangeAxis.POSITION)

        component.beam_path_set_point.is_in_beam = in_beam
        actual = param.is_disabled

        assert_that(actual, is_(expected))

    def test_GIVEN_component_in_beam_sp_rbv_is_out_for_readback_beam_path_THEN_axis_param_is_unaffected(
        self,
    ):
        in_beam = False
        expected = True
        component = Component("test_comp", setup=PositionAndAngle(0, 0, 90))
        param = AxisParameter("param", component, ChangeAxis.POSITION)
        param.is_disabled = expected

        component.beam_path_rbv.is_in_beam = in_beam
        actual = param.is_disabled

        assert_that(actual, is_(expected))

    def test_GIVEN_component_in_beam_sp_rbv_is_in_for_readback_beam_path_THEN_axis_param_is_unaffected(
        self,
    ):
        in_beam = True
        expected = False
        component = Component("test_comp", setup=PositionAndAngle(0, 0, 90))
        param = AxisParameter("param", component, ChangeAxis.POSITION)
        param.is_disabled = expected

        component.beam_path_rbv.is_in_beam = in_beam
        actual = param.is_disabled

        assert_that(actual, is_(expected))


class TestBeamlineOnMove(unittest.TestCase):
    def test_GIVEN_three_beamline_parameters_WHEN_move_1st_THEN_all_move(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[0].move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(1, 1, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_WHEN_move_2nd_THEN_2nd_and_3rd_move(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[1].move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(0, 1, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_WHEN_move_3rd_THEN_3rd_moves(self):
        beamline_parameters, _ = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[2].move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(0, 0, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_and_1_and_3_in_mode_WHEN_move_1st_THEN_parameters_in_the_mode_move(
        self,
    ):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()
        beamline.active_mode = "components1and3"

        beamline_parameters[0].move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(1, 0, 1), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_and_3_in_mode_WHEN_move_1st_THEN_only_2nd_parameter_moved(
        self,
    ):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()
        beamline.active_mode = "just2"

        beamline_parameters[0].move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(1, 0, 0), "beamline parameter move counts")

    def test_GIVEN_three_beamline_parameters_in_mode_WHEN_1st_changed_and_move_beamline_THEN_all_move(
        self,
    ):
        beamline_parameters, beamline = DataMother.beamline_with_3_empty_parameters()

        beamline_parameters[0].sp_no_move = 12.0
        beamline.move = 1
        moves = [
            beamline_parameter.move_component_count for beamline_parameter in beamline_parameters
        ]

        assert_that(moves, contains_exactly(1, 1, 1), "beamline parameter move counts")

    @parameterized.expand([("s1", 12.132, "theta", 4.012), ("s3", 1.123, "theta", 2.342)])
    def test_GIVEN_parameter_with_new_sp_WHEN_theta_moved_independently_THEN_parameter_unchanged(
        self, param, param_sp, theta, theta_sp
    ):
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_s3_theta_detector(spacing)

        param_init_position = bl.parameter(param).rbv

        bl.parameter(param).sp_no_move = param_sp
        bl.parameter(theta).sp_no_move = theta_sp
        bl.parameter(theta).move = 1  # Move only theta

        param_final_position = bl.parameter(param).rbv

        assert_that(param_init_position, is_(close_to(param_final_position, delta=1e-6)))

    @parameterized.expand([("s3_gap", 2.452, "theta", 4.012), ("s3_gap", 4.223, "theta", 1.632)])
    def test_GIVEN_slit_gap_parameter_WHEN_theta_moved_independently_THEN_slit_gap_parameter_unchanged(
        self, param, param_sp, theta, theta_sp
    ):
        spacing = 2.0
        bl, drives = DataMother.beamline_s1_gap_theta_s3_gap_detector(spacing)

        param_init_position = bl.parameter(param).rbv

        bl.parameter(param).sp_no_move = param_sp
        bl.parameter(theta).sp_no_move = theta_sp
        bl.parameter(theta).move = 1  # Move only theta

        param_final_position = bl.parameter(param).rbv

        assert_that(param_final_position, is_(close_to(param_init_position, delta=1e-6)))

    def test_GIVEN_parameter_with_mode_init_and_beamline_set_not_to_reinit_on_move_WHEN_in_mode_but_not_at_init_THEN_move_all_param_does_not_reinit(
        self,
    ):
        sm_angle = 0.0
        init_sm_angle = 45.0
        param_name = "smangle"
        beamline = DataMother.beamline_with_one_mode_init_param_in_mode_and_at_off_init(
            init_sm_angle, sm_angle, param_name
        )

        beamline.move = 1

        assert_that(beamline.parameter(param_name).sp, is_(sm_angle))
        assert_that(beamline.parameter(param_name).sp_changed, is_(False))

    def test_GIVEN_parameter_with_mode_init_and_beamline_set_to_reinit_on_move_WHEN_in_mode_but_not_at_init_THEN_move_all_param_does_reinit(
        self,
    ):
        sm_angle = 0.0
        init_sm_angle = 45.0
        param_name = "smangle"
        beamline = DataMother.beamline_with_one_mode_init_param_in_mode_and_at_off_init(
            init_sm_angle, sm_angle, param_name
        )

        beamline.reinit_mode_on_move = True
        beamline.move = 1

        assert_that(beamline.parameter(param_name).sp, is_(init_sm_angle))
        assert_that(beamline.parameter(param_name).sp_changed, is_(False))


class TestBeamlineParameterReadback(unittest.TestCase):
    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_readback_is_changed(self):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        displacement_parameter = AxisParameter("param", sample, ChangeAxis.POSITION)
        sample.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(displacement, None, None)
        )

        result = displacement_parameter.rbv

        assert_that(result, is_(displacement - beam_height))

    def test_GIVEN_tracking_parameter_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(
        self,
    ):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        displacement = 3.0
        beam_height = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        displacement_parameter = AxisParameter("param", sample, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(displacement, None, None)
        )

        listener.assert_called_with(ParameterReadbackUpdate(displacement - beam_height, None, None))
        assert_that(listener.call_count, is_(2))  # once for beam path and once for physcial move

    def test_GIVEN_reflection_angle_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(
        self,
    ):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        angle = 3.0
        beam_angle = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        angle_parameter = AxisParameter("param", sample, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(angle, None, None)
        )

        listener.assert_called_with(ParameterReadbackUpdate(angle - beam_angle, None, None))

    def test_GIVEN_reflection_angle_on_tilting_component_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(
        self,
    ):
        sample = TiltingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        angle = 3.0
        beam_angle = 1.0
        sample.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        angle_parameter = AxisParameter("param", sample, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(angle, None, None)
        )

        listener.assert_called_with(ParameterReadbackUpdate(angle - beam_angle, None, None))

    def test_GIVEN_component_in_beam_WHEN_set_readback_on_component_THEN_call_back_triggered_on_component_change(
        self,
    ):
        sample = ReflectingComponent("sample", setup=PositionAndAngle(0, 10, 90))
        sample.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(0, None, None)
        )
        state = True

        displacement_parameter = InBeamParameter("param", sample)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)
        sample.beam_path_rbv.is_in_beam = state

        listener.assert_called_with(ParameterReadbackUpdate(state, None, None))

    def test_GIVEN_theta_WHEN_no_next_component_THEN_value_is_nan(self):
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 10, 90))
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

        sample = ThetaComponent("sample", setup=PositionAndAngle(10, 10, 135))
        sample.add_angle_to(s3)
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
        s3.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0)

        theta_comp = ThetaComponent("sample", setup=PositionAndAngle(1, 0, 90))
        theta_comp.add_angle_to(s3)
        theta_comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, 0))

        theta = AxisParameter("param", theta_comp, ChangeAxis.ANGLE)

        result = theta.rbv

        assert_that(result, is_(expected_theta))

    def test_GIVEN_position_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(
        self,
    ):
        component = Component("component", setup=PositionAndAngle(0, 10, 90))
        new_displacement = 1.0
        alarm_severity = 1
        alarm_status = 2
        displacement_parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(new_displacement, alarm_severity, alarm_status)
        )

        listener.assert_called_with(
            ParameterReadbackUpdate(new_displacement, alarm_severity, alarm_status)
        )
        self.assertEqual(displacement_parameter.alarm_severity, alarm_severity)
        self.assertEqual(displacement_parameter.alarm_status, alarm_status)

    def test_GIVEN_position_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(
        self,
    ):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(0.0, None, None)
        )
        new_displacement = 1.0
        alarm_severity = 1
        alarm_status = 2
        displacement_parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        listener = Mock()
        displacement_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(new_displacement, alarm_severity, alarm_status)
        )

        listener.assert_called_once_with(ParameterReadbackUpdate(0.0, None, None))
        self.assertEqual(displacement_parameter.alarm_severity, None)
        self.assertEqual(displacement_parameter.alarm_status, None)

    def test_GIVEN_angle_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(
        self,
    ):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        angle_parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status)
        )

        listener.assert_called_with(ParameterReadbackUpdate(True, alarm_severity, alarm_status))
        self.assertEqual(angle_parameter.alarm_severity, alarm_severity)
        self.assertEqual(angle_parameter.alarm_status, alarm_status)

    def test_GIVEN_angle_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(
        self,
    ):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(0, None, None)
        )
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        angle_parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        listener = Mock()
        angle_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status)
        )

        listener.assert_called_with(ParameterReadbackUpdate(0.0, None, None))
        self.assertEqual(angle_parameter.alarm_severity, None)
        self.assertEqual(angle_parameter.alarm_status, None)

    def test_GIVEN_inbeam_parameter_WHEN_updating_displacement_with_alarms_on_component_THEN_parameter_is_in_alarm_and_propagates_alarm(
        self,
    ):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        new_value = 1.0
        alarm_severity = 1
        alarm_status = 2
        in_beam_parameter = InBeamParameter("param", component)
        listener = Mock()
        in_beam_parameter.add_listener(ParameterReadbackUpdate, listener)
        component.beam_path_rbv.axis[ChangeAxis.POSITION].park_sequence_count = 1

        component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(new_value, alarm_severity, alarm_status)
        )

        listener.assert_called_with(ParameterReadbackUpdate(True, alarm_severity, alarm_status))
        #  once for beam path update and once for physical move update
        assert_that(listener.call_count, is_(2))
        self.assertEqual(in_beam_parameter.alarm_severity, alarm_severity)
        self.assertEqual(in_beam_parameter.alarm_status, alarm_status)

    def test_GIVEN_inbeam_parameter_WHEN_updating_angle_with_alarms_on_component_THEN_parameter_value_and_alarms_are_unchanged(
        self,
    ):
        component = ReflectingComponent("component", setup=PositionAndAngle(0, 10, 90))
        component.beam_path_rbv.axis[ChangeAxis.POSITION].set_displacement(
            CorrectedReadbackUpdate(0, None, None)
        )
        new_angle = 1.0
        alarm_severity = 1
        alarm_status = 2
        in_beam_parameter = InBeamParameter("param", component)
        listener = Mock()
        in_beam_parameter.add_listener(ParameterReadbackUpdate, listener)

        component.beam_path_rbv.axis[ChangeAxis.ANGLE].set_displacement(
            CorrectedReadbackUpdate(new_angle, alarm_severity, alarm_status)
        )

        listener.assert_called_once_with(ParameterReadbackUpdate(True, None, None))
        self.assertEqual(in_beam_parameter.alarm_severity, None)
        self.assertEqual(in_beam_parameter.alarm_status, None)

    def test_GIVEN_direct_parameter_WHEN_updating_value_with_alarm_on_pv_wrapper_THEN_parameter_is_in_alarm_and_propagates_alarm(
        self,
    ):
        pv_wrapper = create_mock_axis("s1vg", 0.0, 1)
        new_value = 1.0
        alarm_severity = 1
        alarm_status = 2
        parameter = DirectParameter("param", pv_wrapper)
        listener = Mock()
        parameter.add_listener(ParameterReadbackUpdate, listener)

        pv_wrapper.trigger_listeners(ReadbackUpdate(new_value, alarm_severity, alarm_status))

        listener.assert_called_once_with(
            ParameterReadbackUpdate(new_value, alarm_severity, alarm_status)
        )
        self.assertEqual(parameter.alarm_severity, alarm_severity)
        self.assertEqual(parameter.alarm_status, alarm_status)


class TestBeamlineThetaComponentWhenDisabled(unittest.TestCase):
    def test_GIVEN_theta_with_0_deg_beam_and_next_component_in_beam_but_disabled_WHEN_set_theta_to_45_THEN_component_sp_is_at_45_degrees(
        self,
    ):
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))

        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector)

        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result = detector.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        assert_that(
            result, is_(close_to(-10.0, 1e-6))
        )  # the beam is now above the current position. The beam line parameter needs to be triggered to make is move

    def test_GIVEN_theta_with_0_deg_beam_and_next_component_in_beam_is_not_disabled_WHEN_set_theta_to_45_THEN_component_sp_is_not_altered(
        self,
    ):
        # this calculation will be done via the beamline not the forced copy of output beam
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector)

        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(True)

        theta.sp = 22.5
        result = detector.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        assert_that(result, is_(close_to(0, 1e-6)))

    def test_GIVEN_theta_with_0_deg_beam_and_next_two_component_in_beam_and_are_disabled_WHEN_set_theta_to_45_THEN_first_component_altered_second_one_not(
        self,
    ):
        # this calculation will be done via the beamline not the forced copy of output beam
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector)
        detector2 = Component("detector", setup=PositionAndAngle(0, 20, 90))
        detector2.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector2)
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)
        detector2.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result1 = detector.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()
        result2 = detector2.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        assert_that(result1, is_(close_to(-10, 1e-6)))
        assert_that(result2, is_(close_to(0, 1e-6)))

    def test_GIVEN_theta_with_0_deg_beam_and_next_first_component_out_of_beam_second_in_beam_and_are_disabled_WHEN_set_theta_to_45_THEN_first_component_not_altered_second_one_is(
        self,
    ):
        # this calculation will be done via the beamline not the forced copy of output beam
        sample = ThetaComponent("sample", setup=PositionAndAngle(0, 0, 90))
        sample.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))
        detector.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector)
        detector2 = Component("detector", setup=PositionAndAngle(0, 20, 90))
        detector2.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, 0))
        sample.add_angle_to(detector2)
        theta = AxisParameter("param", sample, ChangeAxis.ANGLE)
        detector.set_incoming_beam_can_change(False)
        detector.beam_path_set_point.axis[ChangeAxis.POSITION].park_sequence_count = 1
        detector.beam_path_set_point.axis[ChangeAxis.POSITION].is_in_beam = False
        detector2.set_incoming_beam_can_change(False)

        theta.sp = 22.5
        result1 = detector.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()
        result2 = detector2.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam()

        assert_that(result1, is_(close_to(0, 1e-6)))
        assert_that(result2, is_(close_to(-20, 1e-6)))


class TestInitSetpoints(unittest.TestCase):
    def setUp(self):
        setup_autosave({"param_float": 0.1}, {"param_bool": True})
        self.component = Component("component", setup=PositionAndAngle(0, 1, 90))
        self.angle_component = TiltingComponent(
            "angle_component", setup=PositionAndAngle(0, 10, 90)
        )
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

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_autosave_value(
        self,
    ):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_not_in_file"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_tracking_displacement_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_bool"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_angle_parameter_THEN_sp_is_autosave_value(
        self,
    ):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_angle_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_not_in_file"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_angle_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_bool"

        param = AxisParameter(param_name, self.angle_component, ChangeAxis.ANGLE, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_in_beam_parameter_THEN_sp_is_autosave_value(
        self,
    ):
        expected = True
        param_name = "param_bool"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_in_beam_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_not_in_file"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_in_beam_parameter_THEN_sp_is_none(
        self,
    ):
        param_name = "param_float"

        param = InBeamParameter(param_name, self.angle_component, autosave=True)

        self.assertIsNone(param.sp)
        self.assertIsNone(param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_exists_WHEN_creating_direct_parameter_THEN_sp_is_autosave_value(
        self,
    ):
        expected = 0.1
        param_name = "param_float"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_and_autosave_value_does_not_exist_WHEN_creating_direct_parameter_THEN_sp_is_taken_from_motor_instead(
        self,
    ):
        expected = 0.2
        param_name = "param_not_in_file"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_parameter_value_of_wrong_type_WHEN_creating_direct_parameter_THEN_sp_is_taken_from_motor_instead(
        self,
    ):
        expected = 0.2
        param_name = "param_bool"

        param = DirectParameter(param_name, self.jaws, autosave=True)

        self.assertEqual(expected, param.sp)
        self.assertEqual(expected, param.sp_rbv)

    def test_GIVEN_autosave_is_true_WHEN_initialising_tracking_position_THEN_beam_calc_caches_autosaved_offset(
        self,
    ):
        expected = 0.1
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=True)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value

        self.assertEqual(expected, actual)

    def test_GIVEN_autosave_is_false_WHEN_initialising_tracking_position_THEN_beam_calc_has_no_autosaved_offset(
        self,
    ):
        param_name = "param_float"

        param = AxisParameter(param_name, self.component, ChangeAxis.POSITION, autosave=False)
        actual = self.component.beam_path_set_point.axis[ChangeAxis.POSITION].autosaved_value

        self.assertIsNone(actual)


class TestMultiChoiceParameter(unittest.TestCase):
    def test_GIVEN_enum_parameter_WHEN_set_THEN_sp_readback_is_value_and_readback_is_triggered(
        self,
    ):
        opt1 = "opt1"
        opt2 = "opt2"
        param = EnumParameter("name", options=[opt1, opt2])
        mock_listener = Mock()
        param.add_listener(ParameterReadbackUpdate, mock_listener)
        param.sp = opt1

        result = param.sp_rbv

        assert_that(result, is_(opt1))
        mock_listener.assert_called_once()
        args = mock_listener.call_args
        assert_that(args[0][0].value, is_(opt1))

    def test_GIVEN_enum_parameter_WHEN_set_THEN_readback_is_same_as_sp_rbv(self):
        opt1 = "opt1"
        opt2 = "opt2"
        param = EnumParameter("name", options=[opt1, opt2])
        param.sp = "opt1"

        result = param.rbv

        assert_that(result, is_(opt1))

    @patch("ReflectometryServer.parameters.param_string_autosave")
    def test_GIVEN_enum_parameter_WHEN_autosaved_THEN_autosaved_value_is_sp_rbv(self, autosave):
        opt1 = "opt1"
        opt2 = "opt2"

        autosave.read_parameter.return_value = opt2
        param = EnumParameter("name", options=[opt1, opt2])

        result = param.sp_rbv

        assert_that(result, is_(opt2))

    @patch("ReflectometryServer.parameters.param_string_autosave")
    def test_GIVEN_enum_parameter_with_no_options_WHEN_validate_THEN_error(self, autosave):
        autosave.read_parameter.return_value = None
        param = EnumParameter("name", options=[])

        errors = param.validate([])

        assert_that(errors, has_length(1))

    @patch("ReflectometryServer.parameters.param_string_autosave")
    def test_GIVEN_enum_parameter_with_duplicate_options_WHEN_validate_THEN_error(self, autosave):
        autosave.read_parameter.return_value = None
        param = EnumParameter("name", options=["dup", "dup"])

        errors = param.validate([])

        assert_that(errors, has_length(1))

    def test_GIVEN_enum_parameter_WHEN_set_non_option_THEN_error(self):
        opt1 = "opt1"
        opt2 = "opt2"
        param = EnumParameter("name", options=[opt1, opt2])
        param.sp = opt1

        with self.assertRaises(ValueError):
            param.sp = "unknown"

        assert_that(param.sp_rbv, is_("opt1"))


class TestCustomFunctionCall(unittest.TestCase):
    def setUp(self) -> None:
        STATUS_MANAGER.clear_all()

    def test_GIVEN_Parameter_WHEN_move_THEN_custom_function_is_called_with_move_to_and_move_from_values(
        self,
    ):
        mock_func = Mock()
        component = Component("comp", PositionAndAngle(0, 0, 0))
        expected_original_sp = False
        with patch(
            "ReflectometryServer.parameters.param_bool_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = InBeamParameter("myname", component, custom_function=mock_func, autosave=True)

        expected_sp = True

        param.sp = expected_sp

        sleep(0.1)  # wait for thread to run

        mock_func.assert_called_with(expected_sp, expected_original_sp)

    def test_GIVEN_Parameter_with_no_function_WHEN_move_THEN_no_custom_function_is_called_and_there_is_no_error(
        self,
    ):
        component = Component("comp", PositionAndAngle(0, 0, 0))

        param = InBeamParameter("myname", component, autosave=True)

        param.sp = True

        sleep(0.1)  # wait for thread to run

        assert_that(STATUS_MANAGER.error_log, is_(""))

    def test_GIVEN_parameter_with_function_that_takes_time_WHEN_move_THEN_function_returns_immediately(
        self,
    ):
        self.myval = None

        def my_function(*args):
            sleep(1)
            self.myval = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        param = InBeamParameter("myname", component, custom_function=my_function)

        param.sp = True

        assert_that(self.myval, is_(None))

    def test_GIVEN_parameter_with_function_that_causes_an_exception_WHEN_move_THEN_exception_is_put_in_error_log(
        self,
    ):
        expected_text = "Oh Dear"

        def my_function(*args):
            raise ValueError(expected_text)

        component = Component("comp", PositionAndAngle(0, 0, 0))
        param_name = "myname"
        param = InBeamParameter(param_name, component, custom_function=my_function)

        param.sp = True

        sleep(0.1)

        assert_that(STATUS_MANAGER.error_log, contains_string(expected_text))
        assert_that(STATUS_MANAGER.error_log, contains_string(param_name))

    def test_GIVEN_parameter_with_function_returns_a_string_WHEN_move_THEN_string_is_put_in_log(
        self,
    ):
        expected_text = "information!!"

        def my_function(*args):
            return expected_text

        component = Component("comp", PositionAndAngle(0, 0, 0))
        param_name = "myname"
        param = InBeamParameter(param_name, component, custom_function=my_function)

        param.sp = True

        sleep(0.1)

        assert_that(STATUS_MANAGER.error_log, contains_string(expected_text))

    def test_GIVEN_Axis_Parameter_WHEN_move_THEN_custom_function_is_called_with_move_to_and_move_from_values(
        self,
    ):
        mock_func = Mock()
        component = Component("comp", PositionAndAngle(0, 0, 0))
        expected_original_sp = 0.1
        with patch(
            "ReflectometryServer.parameters.param_float_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = AxisParameter(
                "myname", component, ChangeAxis.HEIGHT, custom_function=mock_func, autosave=True
            )

        expected_sp = 0.3

        param.sp = expected_sp

        sleep(0.1)  # wait for thread to run

        mock_func.assert_called_with(expected_sp, expected_original_sp)

    def test_GIVEN_Direct_Parameter_WHEN_move_THEN_custom_function_is_called_with_move_to_and_move_from_values(
        self,
    ):
        mock_func = Mock()
        expected_original_sp = 0.1
        mock_axis = create_mock_axis("axis", expected_original_sp, 1)
        with patch(
            "ReflectometryServer.parameters.param_float_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = DirectParameter("myname", mock_axis, custom_function=mock_func, autosave=True)
        mock_axis.sp = expected_original_sp

        expected_sp = 0.3

        param.sp = expected_sp

        sleep(0.1)  # wait for thread to run

        mock_func.assert_called_with(expected_sp, expected_original_sp)

    def test_GIVEN_Direct_Parameter_WHEN_move_THEN_engineering_correction_is_applied_to_axis_sp(
        self,
    ):
        offset = 2
        correction = ConstantCorrection(2)
        expected_original_sp = 0.1
        mock_axis = create_mock_axis("axis", expected_original_sp, 1)
        with patch(
            "ReflectometryServer.parameters.param_float_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = DirectParameter(
                "myname", mock_axis, engineering_correction=correction, autosave=True
            )
        mock_axis.sp = expected_original_sp

        expected_sp = 0.3

        param.sp = expected_sp
        sleep(0.1)  # wait for thread to run
        assert_that(mock_axis.sp, is_(close_to(expected_sp + offset, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_Direct_Parameter_WHEN_constant_correction_applied_THEN_engineering_correction_is_applied_to_init_sp(
        self,
    ):
        offset = 2
        correction = ConstantCorrection(2)
        initial_pos = 0.1
        mock_axis = create_mock_axis("axis", initial_pos, 1)
        with patch(
            "ReflectometryServer.parameters.param_float_autosave.read_parameter",
            new=Mock(return_value=initial_pos),
        ):
            param = DirectParameter(
                "myname", mock_axis, engineering_correction=correction, autosave=True
            )

        assert_that(mock_axis.rbv, is_(close_to(param.sp - offset, DEFAULT_TEST_TOLERANCE)))

    def test_GIVEN_Slit_Gap_Parameter_WHEN_move_THEN_custom_function_is_called_with_move_to_and_move_from_values(
        self,
    ):
        mock_func = Mock()
        expected_original_sp = 0.1
        mock_axis = create_mock_axis("axis", expected_original_sp, 1)
        with patch(
            "ReflectometryServer.parameters.param_float_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = SlitGapParameter("myname", mock_axis, custom_function=mock_func, autosave=True)
        mock_axis.sp = expected_original_sp

        expected_sp = 0.3

        param.sp = expected_sp

        sleep(0.1)  # wait for thread to run

        mock_func.assert_called_with(expected_sp, expected_original_sp)

    def test_GIVEN_Enum_Parameter_WHEN_move_THEN_custom_function_is_called_with_move_to_and_move_from_values(
        self,
    ):
        mock_func = Mock()
        expected_original_sp = "orig"
        mock_axis = create_mock_axis("axis", expected_original_sp, 1)
        with patch(
            "ReflectometryServer.parameters.param_string_autosave.read_parameter",
            new=Mock(return_value=expected_original_sp),
        ):
            param = EnumParameter("myname", ["orig", "new"], custom_function=mock_func)
        mock_axis.sp = expected_original_sp

        expected_sp = "new"

        param.sp = expected_sp

        sleep(0.1)  # wait for thread to run

        mock_func.assert_called_with(expected_sp, expected_original_sp)


class TestReadonlyParameters(unittest.TestCase):
    def setUp(self):
        # define expected values
        self.sm_z = 10
        self.sm_to_sa_distance = 10
        self.sm_angle_to_set = 22.5
        self.updated_angle = 2 * self.sm_angle_to_set
        self.updated_y = (
            self.sm_to_sa_distance
        )  # height equal to dist as reflected angle at sm is 45 deg

        # Set up beamline
        super_mirror = ReflectingComponent(
            "super mirror", PositionAndAngle(z=self.sm_z, y=0, angle=90)
        )
        self.sm_angle = AxisParameter("sm_angle", super_mirror, ChangeAxis.ANGLE)
        sample = ReflectingComponent(
            "sample", PositionAndAngle(z=self.sm_z + self.sm_to_sa_distance, y=0, angle=90)
        )
        self.displacement_height = AxisParameter(
            "displacement_height", sample, ChangeAxis.DISPLACEMENT_POSITION
        )
        self.displacement_angle = AxisParameter(
            "displacement_angle", sample, ChangeAxis.DISPLACEMENT_ANGLE
        )
        params = [self.sm_angle, self.displacement_height, self.displacement_angle]
        mode = BeamlineMode("mode name", [param.name for param in params])
        self.beamline = Beamline([super_mirror, sample], params, [], [mode])

    def test_GIVEN_incoming_beam_has_changed_but_not_moved_THEN_outgoing_beam_param_sp_rbv_is_not_updated(
        self,
    ):
        assert_that(self.displacement_angle.sp, is_(0))
        assert_that(self.displacement_height.sp, is_(0))
        expected_angle = 0
        expected_y = 0

        self.sm_angle.sp_no_move = self.sm_angle_to_set
        actual_y = self.displacement_height.sp_rbv
        actual_angle = self.displacement_angle.sp_rbv

        assert_that(actual_y, is_(close_to(expected_y, DEFAULT_TEST_TOLERANCE)))
        assert_that(actual_angle, is_(expected_angle))

    def test_GIVEN_incoming_beam_has_changed_WHEN_moving_THEN_outgoing_beam_param_sp_is_updated(
        self,
    ):
        assert_that(self.displacement_angle.sp, is_(0))
        assert_that(self.displacement_height.sp, is_(0))
        expected_angle = self.updated_angle
        expected_y = self.updated_y

        self.sm_angle.sp = self.sm_angle_to_set
        actual_y = self.displacement_height.sp
        actual_angle = self.displacement_angle.sp

        assert_that(actual_y, is_(close_to(expected_y, DEFAULT_TEST_TOLERANCE)))
        assert_that(actual_angle, is_(expected_angle))

    def test_GIVEN_incoming_beam_has_changed_WHEN_moving_THEN_outgoing_beam_param_sp_rbv_is_updated(
        self,
    ):
        initial_value = 0
        assert_that(self.displacement_angle.sp, is_(initial_value))
        assert_that(self.displacement_height.sp, is_(initial_value))
        expected_angle = self.updated_angle
        expected_y = self.updated_y

        self.sm_angle.sp = self.sm_angle_to_set
        actual_y = self.displacement_height.sp_rbv
        actual_angle = self.displacement_angle.sp_rbv

        assert_that(actual_y, is_(close_to(expected_y, DEFAULT_TEST_TOLERANCE)))
        assert_that(actual_angle, is_(expected_angle))


if __name__ == "__main__":
    unittest.main()
