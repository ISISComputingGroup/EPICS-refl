import unittest
from math import fabs


from mock import MagicMock, patch
from hamcrest import *

from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import create_mock_axis

FLOAT_TOLERANCE = 1e-9


class TestHeightDriver(unittest.TestCase):

    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.jaws_driver = DisplacementDriver(self.jaws, self.height_axis)

    def test_GIVEN_component_with_height_setpoint_above_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = 20.0
        expected = 2.0
        self.jaws.beam_path_set_point.set_position_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_component_with_height_setpoint_below_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = -20.0
        expected = 2.0
        self.jaws.beam_path_set_point.set_position_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        target_position = 20.0
        target_duration = 4.0
        expected_velocity = 5.0
        self.jaws.beam_path_set_point.set_position_relative_to_beam(target_position)

        self.jaws_driver.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.sp, is_(target_position))

    def test_GIVEN_displacement_changed_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_after_beam_path_update_listener(listener)
        expected_value = 10.1

        self.height_axis.sp = expected_value

        listener.assert_called_once()
        assert_that(self.jaws.beam_path_rbv.get_displacement(), is_(expected_value))


class TestHeightAndTiltDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position_height, max_velocity_height)

        start_position_tilt = 90.0
        max_velocity_tilt = 10.0
        self.tilt_axis = create_mock_axis("JAWS:TILT", start_position_tilt, max_velocity_tilt)

        self.tilting_jaws = TiltingComponent("component", setup=PositionAndAngle(0.0, 10.0, 90.0))

        self.tilting_jaws_driver_disp = DisplacementDriver(self.tilting_jaws, self.height_axis)
        self.tilting_jaws_driver_ang = AngleDriver(self.tilting_jaws, self.tilt_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        beam_angle = 45.0
        expected = 4.5
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        self.tilting_jaws.beam_path_set_point.set_incoming_beam(beam)
        self.tilting_jaws.beam_path_set_point.set_angle_relative_to_beam(0)

        result = max(self.tilting_jaws_driver_disp.get_max_move_duration(),
                     self.tilting_jaws_driver_ang.get_max_move_duration())

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_multiple_axes_THEN_computed_axis_velocity_is_correct_and_setpoint_set_for_all_axes(self):
        beam_angle = 45.0
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        target_duration = 10.0
        expected_velocity_height = 1.0
        target_position_height = 10.0
        expected_velocity_tilt = 4.5
        target_position_tilt = 135.0
        self.tilting_jaws.beam_path_set_point.set_incoming_beam(beam)
        self.tilting_jaws.beam_path_set_point.set_position_relative_to_beam(0.0)  # move component into beam
        self.tilting_jaws.beam_path_set_point.set_angle_relative_to_beam(90.0)

        self.tilting_jaws_driver_disp.perform_move(target_duration)
        self.tilting_jaws_driver_ang.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(close_to(expected_velocity_height, FLOAT_TOLERANCE)))
        assert_that(self.height_axis.sp, is_(close_to(target_position_height, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.velocity, is_(close_to(expected_velocity_tilt, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.sp, is_(close_to(target_position_tilt, FLOAT_TOLERANCE)))


class TestHeightAndAngleDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("SM:HEIGHT", start_position_height, max_velocity_height)

        start_position_angle = 0.0
        max_velocity_angle = 10.0
        self.angle_axis = create_mock_axis("SM:ANGLE", start_position_angle, max_velocity_angle)

        self.supermirror = ReflectingComponent("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.supermirror.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.supermirror_driver_disp = DisplacementDriver(self.supermirror, self.height_axis)
        self.supermirror_driver_ang = AngleDriver(self.supermirror, self.angle_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        target_angle = 30.0
        expected = 3.0
        self.supermirror.beam_path_set_point.angle = target_angle
        self.supermirror.beam_path_set_point.set_position_relative_to_beam(10.0)

        result = max(self.supermirror_driver_disp.get_max_move_duration(),
                     self.supermirror_driver_ang.get_max_move_duration())

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_multiple_axes_THEN_computed_axis_velocity_is_correct_and_setpoint_set_for_all_axes(
            self):
        target_duration = 10.0
        expected_velocity_height = 1.0
        target_position_height = 10.0
        expected_velocity_angle = 3.0
        target_position_angle = 30.0
        self.supermirror.beam_path_set_point.angle = 30.0
        self.supermirror.beam_path_set_point.set_position_relative_to_beam(10.0)  # move component into beam

        self.supermirror_driver_disp.perform_move(target_duration)
        self.supermirror_driver_ang.perform_move(target_duration)

        assert_that(fabs(self.height_axis.velocity - expected_velocity_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.height_axis.sp - target_position_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.velocity - expected_velocity_angle) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.sp - target_position_angle) <= FLOAT_TOLERANCE)

    def test_GIVEN_angle_changed_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered(self):
        listener = MagicMock()
        self.supermirror.beam_path_rbv.add_after_beam_path_update_listener(listener)
        expected_value = 10.1

        self.angle_axis.sp = expected_value

        listener.assert_called_once()
        assert_that(self.supermirror.beam_path_rbv.angle, is_(expected_value))


class TestHeightDriverInAndOutOfBeam(unittest.TestCase):

    def setUp(self):
        self.start_position = 0.0
        self.max_velocity = 10.0
        self.out_of_beam_position = -20
        self.tolerance_on_out_of_beam_position = 1
        self.height_axis = create_mock_axis("JAWS:HEIGHT", self.start_position, self.max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.jaws_driver = DisplacementDriver(self.jaws, self.height_axis,
                                              out_of_beam_position=self.out_of_beam_position,
                                              tolerance_on_out_of_beam_position=self.tolerance_on_out_of_beam_position)

    def test_GIVEN_component_which_is_disabled_WHEN_calculating_move_duration_THEN_returned_duration_is_time_taken_to_move_to_out_of_beam_position(self):

        expected = - self.out_of_beam_position / self.max_velocity
        self.jaws.beam_path_set_point.is_in_beam = False

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_component_which_is_disabled_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        expected_position = self.out_of_beam_position
        target_duration = 4.0
        expected_velocity = - expected_position / 4.0
        self.jaws.beam_path_set_point.is_in_beam = False

        self.jaws_driver.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.sp, is_(expected_position))

    def test_GIVEN_displacement_changed_to_out_of_beam_position_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_false(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_after_beam_path_update_listener(listener)
        expected_value = False

        self.height_axis.sp = self.out_of_beam_position

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))

    def test_GIVEN_displacement_changed_to_an_in_beam_position_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_true(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_after_beam_path_update_listener(listener)
        expected_value = True

        self.height_axis.sp = self.out_of_beam_position + 2 * self.tolerance_on_out_of_beam_position

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))

    def test_GIVEN_displacement_changed_to_out_of_beam_position_within_tolerance_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_false(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_after_beam_path_update_listener(listener)
        expected_value = False

        self.height_axis.sp = self.out_of_beam_position + self.tolerance_on_out_of_beam_position * 0.9

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))


class BeamlineMoveDurationTest(unittest.TestCase):
    def test_GIVEN_multiple_components_in_beamline_WHEN_triggering_move_THEN_components_move_at_speed_of_slowest_axis(self):
        sm_angle = 0.0
        sm_angle_to_set = 22.5
        supermirror = ReflectingComponent("supermirror", setup=PositionAndAngle(y=0.0, z=10.0, angle=90.0))
        sm_height_axis = create_mock_axis("SM:HEIGHT", 0.0, 10.0)
        sm_angle_axis = create_mock_axis("SM:ANGLE", sm_angle, 10.0)
        supermirror.beam_path_set_point.angle = sm_angle
        supermirror_driver_disp = DisplacementDriver(supermirror, sm_height_axis)
        supermirror_driver_ang = AngleDriver(supermirror, sm_angle_axis)

        slit_2 = Component("slit_2", setup=PositionAndAngle(y=0.0, z=20.0, angle=90.0))
        slit_2_height_axis = create_mock_axis("SLIT2:HEIGHT", 0.0, 10.0)
        slit_2_driver = DisplacementDriver(slit_2, slit_2_height_axis)

        slit_3 = Component("slit_3", setup=PositionAndAngle(y=0.0, z=30.0, angle=90.0))
        slit_3_height_axis = create_mock_axis("SLIT3:HEIGHT", 0.0, 10.0)
        slit_3_driver = DisplacementDriver(slit_3, slit_3_height_axis)

        detector = TiltingComponent("jaws", setup=PositionAndAngle(y=0.0, z=40.0, angle=90.0))
        detector_height_axis = create_mock_axis("DETECTOR:HEIGHT", 0.0, 10.0)
        detector_tilt_axis = create_mock_axis("DETECTOR:TILT", 0.0, 10.0)
        detector_driver_disp = DisplacementDriver(detector, detector_height_axis)
        detector_driver_ang = AngleDriver(detector, detector_tilt_axis)

        smangle = AngleParameter("smangle", supermirror)
        slit_2_pos = TrackingPosition("s2_pos", slit_2)
        slit_3_pos = TrackingPosition("s3_pos", slit_3)
        det_pos = TrackingPosition("det_pos", detector)
        det_ang = AngleParameter("det_ang", detector)

        components = [supermirror, slit_2, slit_3, detector]
        beamline_parameters = [smangle, slit_2_pos, slit_3_pos, det_pos, det_ang]
        drivers = [supermirror_driver_disp, supermirror_driver_ang, slit_2_driver, slit_3_driver, detector_driver_disp, detector_driver_ang]
        mode = BeamlineMode("mode name", [smangle.name, slit_2_pos.name, slit_3_pos.name, det_pos.name, det_ang.name])
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        beamline = Beamline(components, beamline_parameters, drivers, [mode], beam_start)

        beamline.active_mode = mode.name

        slit_2_pos.sp_no_move = 0.0
        slit_3_pos.sp_no_move = 0.0
        det_pos.sp_no_move = 0.0
        det_ang.sp_no_move = 0

        # detector angle axis takes longest
        expected_max_duration = 4.5

        smangle.sp_no_move = sm_angle_to_set
        with patch.object(beamline, '_perform_move_for_all_drivers') as mock:
            beamline.move = 1

            mock.assert_called_with(expected_max_duration)
