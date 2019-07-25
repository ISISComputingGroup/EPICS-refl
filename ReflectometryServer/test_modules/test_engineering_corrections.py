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

    def test_GIVEN_user_function_engineering_correction_on_angle_driver_WHEN_initialise_THEN_rbv_is_error_value(self):
        correction = lambda x: 0
        comp = TiltingComponent("comp", PositionAndAngle(0.0, 0.0, 0.0))
        mock_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        driver = AngleDriver(comp, mock_axis, engineering_correct=UserFunctionCorrection(correction))
        driver.initialise()

        result = comp.beam_path_set_point.angle

        assert_that(result, is_(ENGINEERING_CORRECTION_NOT_POSSIBLE))


class TestEngineeringCorrectionsPureFunction(unittest.TestCase):

    def test_GIVEN_user_function_engineering_correction_which_adds_no_correction_WHEN_set_value_on_axis_THEN_value_is_same_as_set(self):
        def _test_correction(setpoint):
            return 0

        value = 1
        expected_correction = value

        engineering_correction = UserFunctionCorrection(_test_correction)

        result = engineering_correction.to_axis(value)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_user_function_engineering_correction_which_adds_a_correction_of_the_setpoint_on_WHEN_set_value_on_axis_THEN_value_is_double_what_was_set(self):
        def _test_correction(setpoint):
            """Correction is the same as the setpoint so it doubles the correction"""
            return setpoint

        value = 1
        expected_correction = value*2

        engineering_correction = UserFunctionCorrection(_test_correction)

        result = engineering_correction.to_axis(value)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_user_function_engineering_correction_which_adds_a_correction_of_the_setpoint_on_WHEN_get_value_from_axis_THEN_value_is_that_value_minus_the_setpoint(self):
        def _test_correction(setpoint):
            """Correction is the same as the setpoint so it doubles the correction"""
            return setpoint

        setpoint = 3
        axis_readback = 1
        expected_correction = axis_readback - setpoint

        engineering_correction = UserFunctionCorrection(_test_correction)

        result = engineering_correction.from_axis(axis_readback, setpoint)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_user_function_engineering_correction_which_adds_setpoint_and_beamline_param_WHEN_set_value_on_axis_THEN_value_is_twice_value_plus_beamline_parameter_value(self):
        def _test_correction(setpoint, beamline_parameter):
            return setpoint + beamline_parameter

        beamline_value = 2
        comp = Component("param_comp", setup=PositionAndAngle(0, 0, 90))
        beamline_parameter = TrackingPosition("param", comp)
        beamline_parameter.sp = beamline_value

        value = 1
        expected_correction = value * 2 + beamline_value

        engineering_correction = UserFunctionCorrection(_test_correction, beamline_parameter)

        result = engineering_correction.to_axis(value)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))




# Test when a component is not autosaved but has an engineering correction based on its setpoint
# Test that changes a couple of parameters not in the mode, change a parameter with a correction that depends on both those parameters, then click move for a parameter, should not take into account correction
# Same again but click move for all value should be taken into account