import unittest
from math import fabs

from parameterized import parameterized

from mock import MagicMock, patch
from hamcrest import *

from ReflectometryServer import *
from ReflectometryServer.beam_path_calc import BeamPathUpdate
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate, PVWrapperForParameter
from ReflectometryServer.out_of_beam import OutOfBeamPosition, OutOfBeamLookup
from ReflectometryServer.pv_wrapper import IsChangingUpdate
from ReflectometryServer.server_status_manager import STATUS, STATUS_MANAGER
from server_common.channel_access import UnableToConnectToPVException
from ReflectometryServer.test_modules.data_mother import create_mock_axis

FLOAT_TOLERANCE = 1e-9


class TestHeightDriver(unittest.TestCase):

    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True

        self.jaws_driver = IocDriver(self.jaws, ChangeAxis.POSITION, self.height_axis)

    def test_GIVEN_backlash_distance_is_none_WHEN_backlash_distance_checked_THEN_returned_value_is_zero(self):
        expected = 0.0
        self.height_axis.backlash_distance = None
        duration = self.jaws_driver.get_max_move_duration()

        assert_that(duration, is_(expected))

    def test_GIVEN_backlash_velocity_is_none_WHEN_backlash_distance_checked_THEN_returned_value_is_zero(self):
        expected = 0.0
        self.height_axis.backlash_distance = None
        duration = self.jaws_driver.get_max_move_duration()

        assert_that(duration, is_(expected))

    def test_GIVEN_component_with_height_setpoint_above_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = 20.0
        expected = 2.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_component_with_height_setpoint_below_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = -20.0
        expected = 2.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        target_position = 20.0
        target_duration = 4.0
        expected_velocity = 5.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(target_position)

        self.jaws_driver.perform_move(target_duration, True)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.sp, is_(target_position))

    def test_GIVEN_displacement_changed_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_listener(BeamPathUpdate, listener)
        expected_value = 10.1

        self.height_axis.sp = expected_value

        listener.assert_called_once()
        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement(), is_(expected_value))


class TestNonSynchronisedHeightDriver(unittest.TestCase):

    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True

        self.jaws_driver = IocDriver(self.jaws, ChangeAxis.POSITION, self.height_axis, synchronised=False)

    def test_GIVEN_component_with_height_setpoint_below_current_position_and_not_synchronised_WHEN_calculating_move_duration_THEN_returned_0(self):
        target_position = -20.0
        expected = 0.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_on_non_synchronised_axis_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        target_position = 20.0
        target_duration = 4.0
        expected_velocity = self.height_axis.velocity
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(target_position)

        self.jaws_driver.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.sp, is_(target_position))


class TestHeightAndTiltDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position_height, max_velocity_height)

        start_position_tilt = 90.0
        max_velocity_tilt = 10.0
        self.tilt_axis = create_mock_axis("JAWS:TILT", start_position_tilt, max_velocity_tilt)

        self.tilting_jaws = TiltingComponent("component", setup=PositionAndAngle(0.0, 10.0, 90.0))

        self.tilting_jaws_driver_disp = IocDriver(self.tilting_jaws, ChangeAxis.POSITION, self.height_axis)
        self.tilting_jaws_driver_ang = IocDriver(self.tilting_jaws, ChangeAxis.ANGLE, self.tilt_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        beam_angle = 45.0
        expected = 4.5
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        self.tilting_jaws.beam_path_set_point.set_incoming_beam(beam)
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(0)
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed = True

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
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0.0)  # move component into beam
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(90.0)

        self.tilting_jaws_driver_disp.perform_move(target_duration, True)
        self.tilting_jaws_driver_ang.perform_move(target_duration, True)

        assert_that(self.height_axis.velocity, is_(close_to(expected_velocity_height, FLOAT_TOLERANCE)))
        assert_that(self.height_axis.sp, is_(close_to(target_position_height, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.velocity, is_(close_to(expected_velocity_tilt, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.sp, is_(close_to(target_position_tilt, FLOAT_TOLERANCE)))


class TestNonSynchronisedHeightAndTiltDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position_height, max_velocity_height)

        start_position_tilt = 90.0
        max_velocity_tilt = 10.0
        self.tilt_axis = create_mock_axis("JAWS:TILT", start_position_tilt, max_velocity_tilt)
        self.tilt_axis.velocity = 0.123

        self.tilting_jaws = TiltingComponent("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed = True

        self.tilting_jaws_driver_disp = IocDriver(self.tilting_jaws, ChangeAxis.POSITION, self.height_axis)
        self.tilting_jaws_driver_ang = IocDriver(self.tilting_jaws, ChangeAxis.ANGLE, self.tilt_axis,
                                                 synchronised=False)

    def test_GIVEN_multiple_axes_need_to_move_and_one_is_not_synchronised_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        beam_angle = 45.0
        expected = 1.0
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        self.tilting_jaws.beam_path_set_point.set_incoming_beam(beam)
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(0)
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0)

        angle_duration = self.tilting_jaws_driver_ang.get_max_move_duration()
        result = max(self.tilting_jaws_driver_disp.get_max_move_duration(),
                     angle_duration)

        assert_that(result, is_(close_to(expected, FLOAT_TOLERANCE)))
        assert_that(angle_duration, is_(0.0))

    def test_GIVEN_move_duration_and_target_position_set_and_one_is_not_synchronised_WHEN_moving_multiple_axes_THEN_computed_axis_velocity_is_correct_and_setpoint_set_for_all_axes(self):
        beam_angle = 45.0
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        target_duration = 10.0
        expected_velocity_height = 1.0
        target_position_height = 10.0
        expected_velocity_tilt = self.tilt_axis.velocity  # Velocity should not change
        target_position_tilt = 135.0
        self.tilting_jaws.beam_path_set_point.set_incoming_beam(beam)
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0.0)  # move component into beam
        self.tilting_jaws.beam_path_set_point.axis[ChangeAxis.ANGLE].set_relative_to_beam(90.0)

        self.tilting_jaws_driver_disp.perform_move(target_duration)
        self.tilting_jaws_driver_ang.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(close_to(expected_velocity_height, FLOAT_TOLERANCE)))
        assert_that(self.height_axis.sp, is_(close_to(target_position_height, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.velocity, is_(close_to(expected_velocity_tilt, FLOAT_TOLERANCE)))
        assert_that(self.tilt_axis.sp, is_(close_to(target_position_tilt, FLOAT_TOLERANCE)))


class TestHeightAndIocDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("SM:HEIGHT", start_position_height, max_velocity_height)

        start_position_angle = 0.0
        max_velocity_angle = 10.0
        self.angle_axis = create_mock_axis("SM:ANGLE", start_position_angle, max_velocity_angle)

        self.supermirror = ReflectingComponent("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.supermirror.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.supermirror_driver_disp = IocDriver(self.supermirror, ChangeAxis.POSITION, self.height_axis)
        self.supermirror_driver_ang = IocDriver(self.supermirror, ChangeAxis.ANGLE, self.angle_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        target_angle = 30.0
        expected = 3.0
        self.supermirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(target_angle, None, None))
        self.supermirror.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(10.0)
        self.supermirror.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True
        self.supermirror.beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed = True

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
        self.supermirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(30.0, None, None))
        self.supermirror.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(10.0)  # move component into beam

        self.supermirror_driver_disp.perform_move(target_duration, True)
        self.supermirror_driver_ang.perform_move(target_duration, True)

        assert_that(fabs(self.height_axis.velocity - expected_velocity_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.height_axis.sp - target_position_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.velocity - expected_velocity_angle) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.sp - target_position_angle) <= FLOAT_TOLERANCE)

    def test_GIVEN_angle_changed_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered(self):
        listener = MagicMock()
        self.supermirror.beam_path_rbv.add_listener(BeamPathUpdate, listener)
        expected_value = 10.1

        self.angle_axis.sp = expected_value

        listener.assert_called_once()
        assert_that(self.supermirror.beam_path_rbv.axis[ChangeAxis.ANGLE].get_displacement(), is_(expected_value))


class TestHeightDriverInAndOutOfBeam(unittest.TestCase):

    def setUp(self):
        self.start_position = 0.0
        self.max_velocity = 10.0
        self.tolerance_on_out_of_beam_position = 1
        self.out_of_beam_position = OutOfBeamPosition(-20, tolerance=self.tolerance_on_out_of_beam_position)

        self.height_axis = create_mock_axis("JAWS:HEIGHT", self.start_position, self.max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True

        self.jaws_driver = IocDriver(self.jaws, ChangeAxis.POSITION, self.height_axis,
                                     out_of_beam_positions=[self.out_of_beam_position])

    def test_GIVEN_component_which_is_out_of_beam_WHEN_calculating_move_duration_THEN_returned_duration_is_time_taken_to_move_to_out_of_beam_position(self):

        expected = - self.out_of_beam_position.position / self.max_velocity
        self.jaws.beam_path_set_point.is_in_beam = False

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_component_which_is_out_of_beam_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        expected_position = self.out_of_beam_position.position
        target_duration = 4.0
        expected_velocity = - expected_position / 4.0
        self.jaws.beam_path_set_point.is_in_beam = False

        self.jaws_driver.perform_move(target_duration, True)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.sp, is_(expected_position))

    def test_GIVEN_displacement_changed_to_out_of_beam_position_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_false(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_listener(BeamPathUpdate, listener)
        expected_value = False

        self.height_axis.sp = self.out_of_beam_position.position

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))

    def test_GIVEN_displacement_changed_to_an_in_beam_position_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_true(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_listener(BeamPathUpdate, listener)
        expected_value = True

        self.height_axis.sp = self.out_of_beam_position.position + 2 * self.tolerance_on_out_of_beam_position

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))

    def test_GIVEN_displacement_changed_to_out_of_beam_position_within_tolerance_WHEN_listeners_on_axis_triggered_THEN_listeners_on_driving_layer_triggered_and_have_in_beam_is_false(self):
        listener = MagicMock()
        self.jaws.beam_path_rbv.add_listener(BeamPathUpdate, listener)
        expected_value = False

        self.height_axis.sp = self.out_of_beam_position.position + self.tolerance_on_out_of_beam_position * 0.9

        listener.assert_called()
        assert_that(self.jaws.beam_path_rbv.is_in_beam, is_(expected_value))


class TestDriverChanged(unittest.TestCase):
    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.jaws_driver = IocDriver(self.jaws, ChangeAxis.POSITION, self.height_axis)

    def test_GIVEN_value_not_initialised_THEN_driver_reports_not_at_setpoint(self):
        expected = False

        actual = self.jaws_driver.at_target_setpoint()

        assert_that(actual, is_(expected))

    def test_GIVEN_axis_and_component_position_match_THEN_driver_reports_at_setpoint(self):
        expected = True
        self.height_axis.sp = 0.0

        actual = self.jaws_driver.at_target_setpoint()

        assert_that(actual, is_(expected))

    def test_GIVEN_sp_value_set_and_not_moved_to_THEN_driver_reports_not_at_setpoint(self):
        expected = False
        self.height_axis.sp = 0.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(1.0)

        actual = self.jaws_driver.at_target_setpoint()

        assert_that(actual, is_(expected))

    def test_GIVEN_sp_value_set_and_moved_to_THEN_driver_reports_at_setpoint_and_changed_is_false(self):
        expected = True
        self.height_axis.sp = 0.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(1.0)

        self.jaws_driver.perform_move(1)
        actual = self.jaws_driver.at_target_setpoint()
        changed = self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed

        assert_that(actual, is_(expected))
        assert_that(changed, is_(False))

    def test_GIVEN_sp_value_set_and_moved_to_but_no_distance_travelled_THEN_driver_reports_at_setpoint_and_changed_is_false(self):
        expected = True
        self.height_axis.sp = 0.0
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0)

        self.jaws_driver.perform_move(1)
        actual = self.jaws_driver.at_target_setpoint()
        changed = self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed

        assert_that(actual, is_(expected))
        assert_that(changed, is_(False))

    def test_GIVEN_component_sp_is_within_motor_resolution_WHEN_comparing_to_motor_setpoint_THEN_driver_reports_at_setpoint(self):
        expected = True
        # DEFAULT_TEST_TOLERANCE is 1e-9
        self.height_axis.sp = 0.123456789
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].set_relative_to_beam(0.1234567890123456789)

        actual = self.jaws_driver.at_target_setpoint()

        assert_that(actual, is_(expected))


class BeamlineMoveDurationTest(unittest.TestCase):
    def setUp(self):
        sm_angle = 0.0
        supermirror = ReflectingComponent("supermirror", setup=PositionAndAngle(y=0.0, z=10.0, angle=90.0))
        sm_height_axis = create_mock_axis("SM:HEIGHT", 0.0, 10.0)
        sm_angle_axis = create_mock_axis("SM:ANGLE", sm_angle, 10.0)
        supermirror.beam_path_set_point.axis[ChangeAxis.ANGLE].set_displacement(CorrectedReadbackUpdate(sm_angle, None, None))
        supermirror_driver_disp = IocDriver(supermirror, ChangeAxis.POSITION, sm_height_axis)
        supermirror_driver_ang = IocDriver(supermirror, ChangeAxis.ANGLE, sm_angle_axis)

        slit_2 = Component("slit_2", setup=PositionAndAngle(y=0.0, z=20.0, angle=90.0))
        slit_2_height_axis = create_mock_axis("SLIT2:HEIGHT", 0.0, 10.0)
        self.slit_2_driver = MagicMock(IocDriver)
        self.slit_2_driver.get_max_move_duration = MagicMock(return_value=0)

        slit_3 = Component("slit_3", setup=PositionAndAngle(y=0.0, z=30.0, angle=90.0))
        slit_3_height_axis = create_mock_axis("SLIT3:HEIGHT", 0.0, 10.0)
        slit_3_driver = IocDriver(slit_3, ChangeAxis.POSITION, slit_3_height_axis)
        self.slit_3_driver = slit_3_driver

        detector = TiltingComponent("jaws", setup=PositionAndAngle(y=0.0, z=40.0, angle=90.0))
        detector_height_axis = create_mock_axis("DETECTOR:HEIGHT", 0.0, 10.0)
        detector_tilt_axis = create_mock_axis("DETECTOR:TILT", 0.0, 10.0)
        detector_driver_disp = IocDriver(detector, ChangeAxis.POSITION, detector_height_axis)
        detector_driver_ang = IocDriver(detector, ChangeAxis.ANGLE, detector_tilt_axis)

        self.smangle = AxisParameter("smangle", supermirror, ChangeAxis.ANGLE)
        slit_2_pos = AxisParameter("s2_pos", slit_2, ChangeAxis.POSITION)
        self.slit_2_pos = slit_2_pos
        slit_3_pos = AxisParameter("s3_pos", slit_3, ChangeAxis.POSITION)
        self.slit_3_pos = slit_3_pos
        det_pos = AxisParameter("det_pos", detector, ChangeAxis.POSITION)
        det_ang = AxisParameter("det_ang", detector, ChangeAxis.ANGLE)

        components = [supermirror, slit_2, slit_3, detector]
        beamline_parameters = [self.smangle, slit_2_pos, slit_3_pos, det_pos, det_ang]
        self.drivers = [supermirror_driver_disp, supermirror_driver_ang, self.slit_2_driver, slit_3_driver, detector_driver_disp, detector_driver_ang]
        mode = BeamlineMode("mode name", [self.smangle.name, slit_2_pos.name, slit_3_pos.name, det_pos.name, det_ang.name])
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        self.beamline = Beamline(components, beamline_parameters, self.drivers, [mode], beam_start)

        self.beamline.active_mode = mode.name

        slit_2_pos.sp_no_move = 0.0
        slit_3_pos.sp_no_move = 0.0
        det_pos.sp_no_move = 0.0
        det_ang.sp_no_move = 0

    def test_GIVEN_multiple_components_in_beamline_WHEN_triggering_move_THEN_components_move_at_speed_of_slowest_axis(self):
        # detector angle axis takes longest
        expected_max_duration = 4.5
        sm_angle_to_set = 22.5

        self.smangle.sp_no_move = sm_angle_to_set
        with patch.object(self.beamline, '_perform_move_for_all_drivers') as mock:
            self.beamline.move = 1

            mock.assert_called_with(expected_max_duration)

    def test_GIVEN_driver_contains_disconnected_pv_WHEN_beamline_moves_THEN_status_set(self):
        sm_angle_to_set = 22.5

        self.smangle.sp_no_move = sm_angle_to_set
        self.slit_3_pos.sp_no_move = -10
        self.slit_3_driver.perform_move = MagicMock(side_effect=UnableToConnectToPVException("A_PV", "ERROR"))

        self.beamline.move = 1
        assert_that(STATUS_MANAGER.status, is_(STATUS.ERROR))


class BeamlineBacklashMoveDurationTest(unittest.TestCase):

    @parameterized.expand([
        (  # Error when max_vel is 0
            {"max_vel": 0, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 0, "dir": "Pos"},
            {"max_vel": 0, "start": 0, "set": 10, "back_dist": 0, "back_speed": 0, "dir": "Pos"},
            "ERROR"
        ),
        (  # No error when back_speed is 0 if back_dist is also 0
            {"max_vel": 1, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 0, "dir": "Pos"},
            {"max_vel": 1, "start": 0, "set": 10, "back_dist": 0, "back_speed": 0, "dir": "Pos"},
            10  # 10/1
        ),
        (  # No backlash distance
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 0, "set": 10, "back_dist": 0, "back_speed": 0.1, "dir": "Pos"},
            50  # 10/0.2
        ),
        (  # Test where backlash is in same direction as motion
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 0, "set": 10, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            60  # (10-2)/0.2 + 2/0.1
        ),
        (  # Test where backlash is in the opposite direction to set point
            {"max_vel": 20, "start": 0.5, "set": 0, "back_dist": 0, "back_speed": 1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 10, "set": 0, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            80  # (10+2)/0.2 + 2/0.1
        ),
        (  # Test where move starts already within backlash distance
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 0, "set": 1, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            10  # 1/0.1
        ),
        (  # Test where move starts within backlash distance but not from backlash direction
            {"max_vel": 20, "start": 0.5, "set": 0, "back_dist": 0, "back_speed": 1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 1, "set": 0, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            35  # (1+2)/0.2 + 2/0.1
        ),
        (  # Test where both axes have backlash
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0.1, "back_speed": 0.1, "dir": "Pos"},
            {"max_vel": 0.2, "start": 0, "set": 0.1, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            1.02  # (0.5-0.1)/20 + 0.1/0.1
        ),
        (  # Test where backlash is in same direction as motion and axes are Neg
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 0, "set": 10, "back_dist": 2, "back_speed": 0.1, "dir": "Neg"},
            80  # (10+2)/0.2 + 2/0.1
        ),
        (  # Test where backlash is in the opposite direction to set point and axes are Neg
            {"max_vel": 20, "start": 0.5, "set": 0, "back_dist": 0, "back_speed": 1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 10, "set": 0, "back_dist": 2, "back_speed": 0.1, "dir": "Neg"},
            60  # (10-2)/0.2 + 2/0.1
        ),
        (  # Test where move starts already within backlash distance and axes are Neg
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0, "back_speed": 1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 0, "set": 1, "back_dist": 2, "back_speed": 0.1, "dir": "Neg"},
            35  # (1+2)/0.2 + 2/0.1
        ),
        (  # Test where move starts within backlash distance but not from backlash direction and axes are Neg
            {"max_vel": 20, "start": 0.5, "set": 0, "back_dist": 0, "back_speed": 1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 1, "set": 0, "back_dist": 2, "back_speed": 0.1, "dir": "Neg"},
            10  # 1/0.1
        ),
        (  # Test where both axes have backlash and axes are Neg
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0.1, "back_speed": 0.1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 0, "set": 0.1, "back_dist": 2, "back_speed": 0.1, "dir": "Neg"},
            30.5  # (0.1+2)/0.2 + 2/0.1
        ),
        (  # Test where both axes have backlash and one axis is Neg
            {"max_vel": 20, "start": 0, "set": 0.5, "back_dist": 0.1, "back_speed": 0.1, "dir": "Neg"},
            {"max_vel": 0.2, "start": 0, "set": 0.1, "back_dist": 2, "back_speed": 0.1, "dir": "Pos"},
            1.03  # (0.5+0.1)/20 + 0.1/0.1
        ),
    ])
    def test_GIVEN_two_axes_with_backlash_WHEN_triggering_move_THEN_components_move_at_speed_of_slowest_axis(
            self, pos, ang, expected_max_duration):

        detector = TiltingComponent("point_detector", setup=PositionAndAngle(y=0.0, z=6.0, angle=90.0))
        detector_height_axis = create_mock_axis("HEIGHT", pos["start"], pos["max_vel"], pos["back_dist"], pos["back_speed"], pos["dir"])
        detector_tilt_axis = create_mock_axis("TILT", ang["start"], ang["max_vel"], ang["back_dist"], ang["back_speed"], ang["dir"])
        detector_driver_disp = IocDriver(detector, ChangeAxis.POSITION, detector_height_axis)
        detector_driver_ang = IocDriver(detector, ChangeAxis.ANGLE, detector_tilt_axis)
        det_pos = AxisParameter("det_pos", detector, ChangeAxis.POSITION)
        det_ang = AxisParameter("det_ang", detector, ChangeAxis.ANGLE)

        components = [detector]
        beamline_parameters = [det_pos, det_ang]
        drivers = [detector_driver_disp, detector_driver_ang]
        mode = BeamlineMode("mode name",
                            [det_pos.name, det_ang.name])
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        beamline = Beamline(components, beamline_parameters, drivers, [mode], beam_start)

        beamline.active_mode = mode.name

        det_pos.sp_no_move = pos["set"]
        det_ang.sp_no_move = ang["set"]

        with patch.object(beamline, '_perform_move_for_all_drivers') as mock:
            beamline.move = 1

            if expected_max_duration == "ERROR":
                mock.assert_not_called()
            else:
                mock.assert_called_with(expected_max_duration)


class TestIocDriverWithAxesDependentOnParam(unittest.TestCase):

    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)
        self.alt_axis = create_mock_axis("JAWS:NORTH", start_position, max_velocity)

        self.jaws = Component("component", setup=PositionAndAngle(0.0, 10.0, 90.0))
        self.jaws.beam_path_set_point.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))
        self.jaws.beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = True

        self.opt1 = "height_axis"
        self.opt2 = "alt_axis"
        self.opt3 = "other"
        self.param = EnumParameter("param", options=[self.opt1, self.opt2, self.opt3])

        self.jaws_driver = IocDriver(self.jaws, ChangeAxis.POSITION, self.height_axis,
                                     pv_wrapper_for_parameter=PVWrapperForParameter(self.param, {self.opt2: self.alt_axis}))

    def test_GIVEN_component_WHEN_both_axis_moves_THEN_displacement_is_axis_value(self):
        expected = 1
        self.height_axis.sp = expected
        self.alt_axis.sp = 99

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement(), is_(expected))

    def test_GIVEN_component_and_param_set_to_alt_WHEN_alt_axis_moves_THEN_displacement_is_alt_axis_value(self):
        expected = 1
        self.param.sp = self.opt2

        self.height_axis.sp = 99
        self.alt_axis.sp = expected

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement(), is_(expected))

    def test_GIVEN_component_and_axis_position_set_WHEN_change_param_THEN_displacement_changes(self):
        expected = 1
        self.height_axis.sp =99
        self.alt_axis.sp = expected

        self.param.sp = self.opt2

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement(), is_(expected))

    def test_GIVEN_component_and_axis_position_set_WHEN_change_param_to_non_change_THEN_displacement_changes_to_default_axis(self):
        expected = 1
        self.height_axis.sp = expected
        self.alt_axis.sp = 99
        self.param.sp = self.opt2

        self.param.sp = self.opt3

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].get_displacement(), is_(expected))

    def test_GIVEN_component_and_param_set_to_alt_WHEN_alt_axis_changes_THEN_change_is_alt_axis_value(self):
        expected = True
        self.param.sp = self.opt2

        # set before and after to make sure that listeners are being removed
        self.height_axis.trigger_listeners(IsChangingUpdate(not expected, None, None))
        self.alt_axis.trigger_listeners(IsChangingUpdate(expected, None, None))
        self.height_axis.trigger_listeners(IsChangingUpdate(not expected, None, None))

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing, is_(expected))

    def test_GIVEN_component_and_axis_set_to_changing_WHEN_switch_axis_THEN_is_changing_true(self):
        expected = True
        self.height_axis.trigger_listeners(IsChangingUpdate(not expected, None, None))
        self.alt_axis.trigger_listeners(IsChangingUpdate(expected, None, None))

        self.param.sp = self.opt2

        assert_that(self.jaws.beam_path_rbv.axis[ChangeAxis.POSITION].is_changing, is_(expected))

    def test_GIVEN_axis_to_change_on_param_WHEN_init_THEN_all_axes_are_initialised(self):
        self.jaws_driver.initialise()

        assert_that(self.height_axis.is_initialised, is_(True))
        assert_that(self.alt_axis.is_initialised, is_(True))


class TestIOCDriverInAndOutOfBeamWithOffsetOutOfBeamPosition(unittest.TestCase):

    @parameterized.expand([(0,), (1,)])
    def test_GIVEN_out_of_beam_with_offset_WHEN_move_THEN_component_moves_to_correct_place(self, correction):
        offset = 10
        beam_height = 2
        expected_position = beam_height + offset + correction

        comp = Component("Comp", PositionAndAngle(0, 1, 90))
        mock_axis = create_mock_axis("axis", 0, 1)
        iocDriver = IocDriver(comp, ChangeAxis.POSITION, mock_axis,
                              out_of_beam_positions=[OutOfBeamPosition(offset, is_offset=True)],
                              engineering_correction=ConstantCorrection(correction))

        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))
        comp.beam_path_set_point.is_in_beam = False

        iocDriver.perform_move(1)

        result = mock_axis.sp

        assert_that(result, is_(expected_position))

    def test_GIVEN_out_of_beam_with_offset_on_angle_WHEN_move_THEN_component_moves_to_correct_place(self):
        offset = 10
        beam_angle = 2
        expected_position = beam_angle + offset

        comp = TiltingComponent("Comp", PositionAndAngle(0, 1, 90))
        mock_axis = create_mock_axis("axis", 0, 1)
        iocDriver = IocDriver(comp, ChangeAxis.ANGLE, mock_axis, out_of_beam_positions=[OutOfBeamPosition(offset, is_offset=True)])

        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))
        comp.beam_path_set_point.is_in_beam = False

        iocDriver.perform_move(1)

        result = mock_axis.sp

        assert_that(result, is_(expected_position))

    def test_GIVEN_out_of_beam_with_offset_WHEN_axis_move_THEN_component_in_beam_is_out(self):
        offset = 10
        beam_height = 2
        comp = Component("Comp", PositionAndAngle(0, 1, 90))
        mock_axis = create_mock_axis("axis", 0, 1)
        IocDriver(comp, ChangeAxis.POSITION, mock_axis, out_of_beam_positions=[OutOfBeamPosition(offset, is_offset=True)])

        comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))

        mock_axis.sp = offset + beam_height

        result = comp.beam_path_rbv.is_in_beam

        assert_that(result, is_(False))

    def test_GIVEN_out_of_beam_with_offset_for_angle_WHEN_axis_move_THEN_component_in_beam_is_out(self):
        offset = 10
        beam_angle = 2
        comp = TiltingComponent("Comp", PositionAndAngle(0, 1, 90))
        mock_axis = create_mock_axis("axis", 0, 1)
        IocDriver(comp, ChangeAxis.ANGLE, mock_axis, out_of_beam_positions=[OutOfBeamPosition(offset, is_offset=True)])

        comp.beam_path_rbv.set_incoming_beam(PositionAndAngle(0, 0, beam_angle))

        mock_axis.sp = offset + beam_angle

        result = comp.beam_path_rbv.is_in_beam

        assert_that(result, is_(False))

    def test_GIVEN_out_of_beam_with_offset_for_angle_WHEN_init_THEN_component_is_out_of_beam(self):
        offset = 10
        beam_height = 2
        comp = Component("Comp", PositionAndAngle(0, 1, 90))
        mock_axis = create_mock_axis("axis", 0, 1)
        mock_axis.sp = offset + beam_height
        iocdriver = IocDriver(comp, ChangeAxis.POSITION, mock_axis,
                  out_of_beam_positions=[OutOfBeamPosition(offset, is_offset=True)])

        comp.beam_path_set_point.set_incoming_beam(PositionAndAngle(beam_height, 0, 0))

        iocdriver.initialise_setpoint()

        result = comp.beam_path_set_point.is_in_beam

        assert_that(result, is_(False))
