from hamcrest import *

import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import MockChannelAccess, create_mock_axis

from server_common.channel_access import UnableToConnectToPVException

FLOAT_TOLERANCE = 1e-9


class TestEngineeringCorrections(unittest.TestCase):

    def _setup_driver_axis_and_correction(self, correction):
        comp = Component("comp", PositionAndAngle(0.0, 0.0, 0.0))
        mock_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        driver = DisplacementDriver(comp, mock_axis, engineering_correct=ConstantCorrection(correction))
        driver._is_changed = lambda: True  # simulate that the component has requested a change
        return driver, mock_axis, comp

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_driver_told_to_go_to_0_THEN_pv_sent_to_1(self):
        expected_correction = 1
        driver, mock_axis, comp = self._setup_driver_axis_and_correction(expected_correction)
        driver.perform_move(1)

        result = mock_axis.sp

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_engineering_correction_offset_of_1_on_angle_driver_WHEN_driver_told_to_go_to_0_THEN_pv_sent_to_1(self):
        expected_correction = 1
        comp = TiltingComponent("comp", PositionAndAngle(0.0, 0.0, 0.0))
        mock_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        driver = AngleDriver(comp, mock_axis, engineering_correct=ConstantCorrection(expected_correction))
        driver._is_changed = lambda: True  # simulate that the component has requested a change
        driver.perform_move(1)

        result = mock_axis.sp

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_driver_is_at_2_THEN_read_back_is_at_1(self):
        expected_correct_value = 1
        correction = 1
        move_to = expected_correct_value + correction
        driver, mock_axis, comp = self._setup_driver_axis_and_correction(correction)
        mock_axis.sp = move_to

        result = comp.beam_path_rbv.get_displacement()

        assert_that(result, is_(close_to(expected_correct_value, FLOAT_TOLERANCE)))

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_at_set_point_THEN_at_target_setpoint_is_true(self):
        correction = 4
        driver, mock_axis, comp = self._setup_driver_axis_and_correction(correction)
        comp.beam_path_set_point.set_displacement(2, None, None)
        driver.perform_move(1)

        result = driver.at_target_setpoint()

        assert_that(result, is_(True), "Axis is at set point")

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_construct_THEN_rbv_set_correctly(self):
        correction = 4
        driver, mock_axis, comp = self._setup_driver_axis_and_correction(correction)

        result = driver.rbv_cache()

        assert_that(result, is_(-1 * correction))

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_initialise_THEN_rbv_set_correctly(self):
        correction = 4
        driver, mock_axis, comp = self._setup_driver_axis_and_correction(correction)
        driver.initialise()

        result = comp.beam_path_set_point.get_displacement()

        assert_that(result, is_(-1 * correction))

    def test_GIVEN_engineering_correction_offset_of_1_on_angle_driver_WHEN_initialise_THEN_rbv_set_correctly(self):
        correction = 1
        comp = TiltingComponent("comp", PositionAndAngle(0.0, 0.0, 0.0))
        mock_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        driver = AngleDriver(comp, mock_axis, engineering_correct=ConstantCorrection(correction))
        driver.initialise()

        result = comp.beam_path_set_point.angle

        assert_that(result, is_(-1 * correction))
