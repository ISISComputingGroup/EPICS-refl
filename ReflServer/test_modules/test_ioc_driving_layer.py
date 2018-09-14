import unittest
from math import fabs
from mock import MagicMock, PropertyMock, patch
from hamcrest import *

from ReflServer.beamline import Beamline, BeamlineMode
from ReflServer.components import TiltingJaws, Component, ReflectingComponent
from ReflServer.movement_strategy import LinearMovement
from ReflServer.gemoetry import PositionAndAngle
from ReflServer.ioc_driver import HeightDriver, HeightAndTiltDriver, HeightAndAngleDriver
from ReflServer.parameters import ReflectionAngle, TrackingPosition

FLOAT_TOLERANCE = 1e-9


def create_mock_axis(name, init_position, max_velocity):
    axis = MagicMock()
    axis.name = name
    axis.value = init_position
    axis.max_velocity = max_velocity
    return axis


class TestHeightDriver(unittest.TestCase):

    def setUp(self):
        start_position = 0.0
        max_velocity = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position, max_velocity)

        self.jaws = Component("component", movement_strategy=LinearMovement(0.0, 10.0, 90.0))
        self.jaws.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.jaws_driver = HeightDriver(self.jaws, self.height_axis)

    def test_GIVEN_component_with_height_setpoint_above_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = 20.0
        expected = 2.0
        self.jaws.set_position_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_component_with_height_setpoint_below_current_position_WHEN_calculating_move_duration_THEN_returned_duration_is_correct(self):
        target_position = -20.0
        expected = 2.0
        self.jaws.set_position_relative_to_beam(target_position)

        result = self.jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_axis_THEN_computed_axis_velocity_is_correct_and_setpoint_set(self):
        target_position = 20.0
        target_duration = 4.0
        expected_velocity = 5.0
        self.jaws.set_position_relative_to_beam(target_position)

        self.jaws_driver.perform_move(target_duration)

        assert_that(self.height_axis.velocity, is_(expected_velocity))
        assert_that(self.height_axis.value, is_(target_position))


class TestHeightAndTiltDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("JAWS:HEIGHT", start_position_height, max_velocity_height)

        start_position_tilt = 0.0
        max_velocity_tilt = 10.0
        self.tilt_axis = create_mock_axis("JAWS:TILT", start_position_tilt, max_velocity_tilt)

        self.tilting_jaws = TiltingJaws("component", movement_strategy=LinearMovement(0.0, 10.0, 90.0))

        self.tilting_jaws_driver = HeightAndTiltDriver(self.tilting_jaws, self.height_axis, self.tilt_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        beam_angle = 45.0
        expected = 4.5
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        self.tilting_jaws.set_incoming_beam(beam)

        result = self.tilting_jaws_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_multiple_axes_THEN_computed_axis_velocity_is_correct_and_setpoint_set_for_all_axes(self):
        beam_angle = 45.0
        beam = PositionAndAngle(0.0, 0.0, beam_angle)
        target_duration = 10.0
        expected_velocity_height = 1.0
        target_position_height = 10.0
        expected_velocity_tilt = 4.5
        target_position_tilt = 135.0
        self.tilting_jaws.set_incoming_beam(beam)
        self.tilting_jaws.set_position_relative_to_beam(0.0)  # move component into beam

        self.tilting_jaws_driver.perform_move(target_duration)

        assert_that(fabs(self.height_axis.velocity - expected_velocity_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.height_axis.value - target_position_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.tilt_axis.velocity - expected_velocity_tilt) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.tilt_axis.value - target_position_tilt) <= FLOAT_TOLERANCE)


class TestHeightAndAngleDriver(unittest.TestCase):
    def setUp(self):
        start_position_height = 0.0
        max_velocity_height = 10.0
        self.height_axis = create_mock_axis("SM:HEIGHT", start_position_height, max_velocity_height)

        start_position_angle = 0.0
        max_velocity_angle = 10.0
        self.angle_axis = create_mock_axis("SM:ANGLE", start_position_angle, max_velocity_angle)

        self.supermirror = Component("component", movement_strategy=LinearMovement(0.0, 10.0, 90.0))
        self.supermirror.set_incoming_beam(PositionAndAngle(0.0, 0.0, 0.0))

        self.supermirror_driver = HeightAndAngleDriver(self.supermirror, self.height_axis, self.angle_axis)

    def test_GIVEN_multiple_axes_need_to_move_WHEN_computing_move_duration_THEN_maximum_duration_is_returned(self):
        target_angle = 30.0
        expected = 3.0
        self.supermirror.angle = target_angle
        self.supermirror.set_position_relative_to_beam(10.0)

        result = self.supermirror_driver.get_max_move_duration()

        assert_that(result, is_(expected))

    def test_GIVEN_move_duration_and_target_position_set_WHEN_moving_multiple_axes_THEN_computed_axis_velocity_is_correct_and_setpoint_set_for_all_axes(
            self):
        target_duration = 10.0
        expected_velocity_height = 1.0
        target_position_height = 10.0
        expected_velocity_angle = 3.0
        target_position_angle = 30.0
        self.supermirror.angle = 30.0
        self.supermirror.set_position_relative_to_beam(10.0)  # move component into beam

        self.supermirror_driver.perform_move(target_duration)

        assert_that(fabs(self.height_axis.velocity - expected_velocity_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.height_axis.value - target_position_height) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.velocity - expected_velocity_angle) <= FLOAT_TOLERANCE)
        assert_that(fabs(self.angle_axis.value - target_position_angle) <= FLOAT_TOLERANCE)


class BeamlineMoveDurationTest(unittest.TestCase):
    def test_GIVEN_multiple_components_in_beamline_WHEN_triggering_move_THEN_components_move_at_speed_of_slowest_axis(self):
        sm_angle = 0.0
        sm_angle_to_set = 22.5
        supermirror = ReflectingComponent("supermirror", movement_strategy=LinearMovement(y_position=0.0, z_position=10.0, angle=90.0))
        sm_height_axis = create_mock_axis("SM:HEIGHT", 0.0, 10.0)
        sm_angle_axis = create_mock_axis("SM:ANGLE", sm_angle, 10.0)
        supermirror.angle = sm_angle
        supermirror_driver = HeightAndAngleDriver(supermirror, sm_height_axis, sm_angle_axis)

        slit_2 = Component("slit_2", movement_strategy=LinearMovement(y_position=0.0, z_position=20.0, angle=90.0))
        slit_2_height_axis = create_mock_axis("SLIT2:HEIGHT", 0.0, 10.0)
        slit_2_driver = HeightDriver(slit_2, slit_2_height_axis)

        slit_3 = Component("slit_3", movement_strategy=LinearMovement(y_position=0.0, z_position=30.0, angle=90.0))
        slit_3_height_axis = create_mock_axis("SLIT3:HEIGHT", 0.0, 10.0)
        slit_3_driver = HeightDriver(slit_3, slit_3_height_axis)

        detector = TiltingJaws("jaws", movement_strategy=LinearMovement(y_position=0.0, z_position=40.0, angle=90.0))
        detector_height_axis = create_mock_axis("DETECTOR:HEIGHT", 0.0, 10.0)
        detector_tilt_axis = create_mock_axis("DETECTOR:TILT", 0.0, 10.0)
        detector_driver = HeightAndTiltDriver(detector, detector_height_axis, detector_tilt_axis)

        smangle = ReflectionAngle("smangle", supermirror)
        slit_2_pos = TrackingPosition("s2_pos", slit_2)
        slit_3_pos = TrackingPosition("s3_pos", slit_3)
        det_pos = TrackingPosition("det_pos", detector)
        components = [supermirror, slit_2, slit_3, detector]
        beamline_parameters = [smangle, slit_2_pos, slit_3_pos, det_pos]
        drivers = [supermirror_driver, slit_2_driver, slit_3_driver, detector_driver]
        mode = BeamlineMode("mode name", [smangle.name, slit_2_pos.name, slit_3_pos.name, det_pos.name])
        beamline = Beamline(components, beamline_parameters, drivers, [mode])

        beamline.active_mode = mode

        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        beamline.set_incoming_beam(beam_start)
        slit_2_pos.sp_no_move = 0.0
        slit_3_pos.sp_no_move = 0.0
        det_pos.sp_no_move = 0.0

        # detector angle axis takes longest
        expected_max_duration = 4.5

        smangle.sp_no_move = sm_angle_to_set
        with patch.object(beamline, '_move_drivers') as mock:
            beamline.move = 1

            mock.assert_called_with(expected_max_duration)
