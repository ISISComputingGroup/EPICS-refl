import io

from hamcrest import *
from mock import patch
from parameterized import parameterized

import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer import beamline_configuration
from ReflectometryServer.engineering_corrections import InterpolateGridDataCorrectionFromProvider
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


class TestEngineeringCorrectionsLinear(unittest.TestCase):

    def setUp(self):
        self._file_contents = ""

    @parameterized.expand([(1.0, 1.234),  # first point in grid
                           (2.0, 4.0),     # second point in grid
                           (1.5, (4.0 - 1.234)/2 + 1.234),  # halfway between 1st and 2nd point
                           (1.25, (4.0 - 1.234)/4 + 1.234),  # quarter of the way between 1st and 2nd point
                           (0.9, 0),  # outside the grid before first point
                           (3.1, 0)  # outside the grid after last point
                           ])
    def test_GIVEN_interp_with_1D_points_based_on_setpoint_of_axis_WHEN_request_a_point_THEN_correction_returned_for_that_point_with_interpolation_if_needed(self, value, expected_correction):
        grid_data_provider = GridDataFileReader("Test")
        grid_data_provider.variables = ["driver"]
        grid_data_provider.points = np.array([[1.0, ], [2.0, ], [3.0, ]])
        grid_data_provider.corrections = np.array([1.234, 4.0, 6.0])
        grid_data_provider.read = lambda: None

        interp = InterpolateGridDataCorrectionFromProvider(grid_data_provider=grid_data_provider)

        result = interp.correction(value)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    @parameterized.expand([(1.0, 1.234),  # first point in grid
                           (2.0, 4.0),     # second point in grid
                           (1.5, (4.0 - 1.234)/2 + 1.234),  # halfway between 1st and 2nd point
                           (1.25, (4.0 - 1.234)/4 + 1.234),  # quarter of the way between 1st and 2nd point
                           (0.9, 0),  # outside the grid before first point
                           (3.1, 0)  # outside the grid after last point
                           ])
    def test_GIVEN_interp_with_1D_points_based_on_setpoint_of_beamline_parameter_WHEN_request_a_point_THEN_correction_returned_for_that_point_with_interpolation_if_needed(self, value, expected_correction):
        grid_data_provider = GridDataFileReader("Test")
        grid_data_provider.variables = ["Theta"]
        grid_data_provider.points = np.array([[1.0, ], [2.0, ], [3.0, ]])
        grid_data_provider.corrections = np.array([1.234, 4.0, 6.0])
        grid_data_provider.read = lambda: None

        comp = Component("param_comp", setup=PositionAndAngle(0, 0, 90))
        beamline_parameter = TrackingPosition("theta", comp)
        beamline_parameter.sp = value

        interp = InterpolateGridDataCorrectionFromProvider(grid_data_provider, beamline_parameter)
        interp.grid_data_provider = grid_data_provider

        result = interp.correction(0)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    @parameterized.expand([(1.0, 1.0, 1.234),  # first point in grid
                           (2.0, 6.0, 5.0),     # second point in grid
                           (1.5, 1.0, (4.0 - 1.234)/2 + 1.234),  # value (2.617) halfway between 1st and 2nd point
                           (1.0, 3.5, (2.234 - 1.234) / 2 + 1.234),  # value (1.734) halfway between 1st and 4th point
                           (1.5, 3.5, (1.234 + 2.234 + 4.0 + 5.0) / 4),  # halfway between 1st, 2nd, 3rd and 4th point
                           (0.9, 1.1, 0),  # outside the grid in value
                           (2.1, 6.1, 0)  # outside the grid in theta
                           ])
    def test_GIVEN_interp_with_2D_points_based_on_setpoint_of_beamline_parameter_WHEN_request_a_point_THEN_correction_returned_for_that_point_with_interpolation_if_needed(self, value, theta, expected_correction):
        grid_data_provider = GridDataFileReader("Test")
        grid_data_provider.variables = ["driver", "Theta"]
        grid_data_provider.points = np.array([[1.0, 1.0], [2.0, 1.0], [3.0, 1.0], [1.0, 6.0], [2.0, 6.0], [3.0, 6.0]])
        grid_data_provider.corrections = np.array([1.234, 4.0, 6.0, 2.234, 5.0, 7.0])
        grid_data_provider.read = lambda: None

        comp = Component("param_comp", setup=PositionAndAngle(0, 0, 90))
        beamline_parameter = TrackingPosition("theta", comp)
        beamline_parameter.sp = theta

        interp = InterpolateGridDataCorrectionFromProvider(grid_data_provider, beamline_parameter)

        result = interp.correction(value)

        assert_that(result, is_(close_to(expected_correction, FLOAT_TOLERANCE)))

    def test_GIVEN_interp_with_1D_points_based_on_setpoint_of_beamline_parameter_WHEN_column_name_not_beamline_name_THEN_error_in_initialise(self):
        grid_data_provider = GridDataFileReader("Test")
        grid_data_provider.variables = ["Theta"]
        grid_data_provider.points = np.array([[1.0, ], [2.0, ], [3.0, ]])
        grid_data_provider.corrections = np.array([1.234, 4.0, 6.0])
        grid_data_provider.read = lambda: None

        comp = Component("param_comp", setup=PositionAndAngle(0, 0, 90))
        beamline_parameter = TrackingPosition("not theta", comp)

        assert_that(
            calling(InterpolateGridDataCorrectionFromProvider).with_args(grid_data_provider, beamline_parameter),
            raises(ValueError))


class Test1DInterpolationFileReader(unittest.TestCase):

    def test_GIVEN_file_reader_WHEN_file_does_not_exist_THEN_error(self):
        reader = GridDataFileReader("non_existant_filename")

        assert_that(calling(reader.read), raises(IOError, ".*No such file.*"))

    def test_GIVEN_1d_interp_WHEN_file_does_exist_but_is_empty_THEN_error(self):
        beamline_configuration.REFL_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_config", "good_config", "refl"))
        reader = GridDataFileReader("blankfile.dat")

        assert_that(calling(reader.read), raises(IOError, "No data found.*"))

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_a_good_file_WHEN_get_correction_details_THEN_description_returned(self, open_file_mock):
        expected_variable_name = "name"
        _file_contents = [u"  {}  , correction".format(expected_variable_name),
                          u"1, 2",
                          u"2, 3"]
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")

        correction.read()
        result = correction.variables

        assert_that(result, is_([expected_variable_name]))

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_a_header_missing_variable_WHEN_read_file_THEN_error(self, open_file_mock):
        expected_variable_name = "name"
        _file_contents = [u"correction".format(expected_variable_name),
                          u"1, 2",
                          u"2, 3"]
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")

        assert_that(calling(correction.read), raises(IOError))

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_different_item_count_in_a_row_WHEN_read_file_THEN_error(self, open_file_mock):
        _file_contents = [u"name, correction",
                          u"1, 2, 3",
                          u"2, 3"]
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")

        assert_that(calling(correction.read), raises(IOError))

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_string_in_csv_WHEN_read_file_THEN_error(self, open_file_mock):
        _file_contents = [u"name, correction",
                          u"1, orange",
                          u"2, 3"]
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")
        assert_that(calling(correction.read), raises(IOError, "Problem with data in.*"))

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_header_and_data_WHEN_read_file_THEN_data_is_as_given(self, open_file_mock):
        expected_correction = [2.0, 4.0, 6.0]
        expected_values = [1, 2.0, 3]

        _file_contents = [u"name, correction"]
        for value, correction in zip(expected_values, expected_correction):
            _file_contents.append(u"{}, {}".format(value, correction))
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")

        correction.read()

        assert_that(correction.corrections, contains(*expected_correction), "corrections")
        assert_that(correction.points, contains(*expected_values), "values")

    @patch("ReflectometryServer.engineering_corrections.GridDataFileReader._open_file")
    def test_GIVEN_1d_interp_with_header_and_data_with_2_d_WHEN_read_file_THEN_data_is_as_given(self, open_file_mock):
        expected_correction = [2.0, 4.0, 6.0]
        expected_values = [[1, 6], [2.0, 4], [3, -10]]

        _file_contents = [u"name1, name2, correction"]
        for (value1, value2), correction in zip(expected_values, expected_correction):
            _file_contents.append(u"{}, {}, {}".format(value1, value2, correction))
        open_file_mock.configure_mock(return_value=io.StringIO("\n".join(_file_contents)))
        correction = GridDataFileReader("")

        correction.read()

        assert_that(correction.corrections, contains(*expected_correction), "corrections")
        for expected_value, value in zip(expected_values, correction.points):
            assert_that(expected_value, contains(*value), "values")


class TestEngineeringCorrectionsChangeListener(unittest.TestCase):

    def setUp(self):
        self.engineering_correction_update = None
        self.engineering_correction_update2 = None

    def _setup_driver_axis_and_correction(self, correction):
        comp = Component("comp", PositionAndAngle(0.0, 0.0, 0.0))
        mock_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        engineering_correct = ConstantCorrection(correction)
        driver = DisplacementDriver(comp, mock_axis, engineering_correct=engineering_correct)
        driver._is_changed = lambda: True  # simulate that the component has requested a change
        return driver, mock_axis, comp, engineering_correct

    def _record_event(self, engineering_correction_update):
        self.engineering_correction_update = engineering_correction_update

    def _record_event2(self, engineering_correction_update):
        self.engineering_correction_update2 = engineering_correction_update

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_driver_told_to_go_to_0_THEN_event_is_triggered_with_description_and_value(self):
        expected_correction = 1
        driver, mock_axis, comp, engineering_correct = self._setup_driver_axis_and_correction(expected_correction)
        driver.add_listener(CorrectionUpdate, self._record_event)

        driver.perform_move(1)

        assert_that(self.engineering_correction_update.correction, is_(close_to(expected_correction, FLOAT_TOLERANCE)))
        assert_that(self.engineering_correction_update.description, all_of(contains_string(engineering_correct.description),
                                                                           contains_string(comp.name),
                                                                           contains_string(mock_axis.name)))

    def test_GIVEN_engineering_correction_offset_of_1_WHEN_driver_is_at_2_THEN_event_is_triggered_with_description_and_value(self):
        expected_correct_value = 1
        correction = 1
        move_to = expected_correct_value + correction
        driver, mock_axis, comp, engineering_correct = self._setup_driver_axis_and_correction(correction)
        mock_axis.sp = move_to
        driver.add_listener(CorrectionUpdate, self._record_event)

        mock_axis.trigger_rbv_change()

        assert_that(self.engineering_correction_update.correction, is_(close_to(correction, FLOAT_TOLERANCE)))
        assert_that(self.engineering_correction_update.description, all_of(contains_string(engineering_correct.description),
                                                                           contains_string(comp.name),
                                                                           contains_string(mock_axis.name)))


# Test when a component is not autosaved but has an engineering correction based on its setpoint
# Test that changes a couple of parameters not in the mode, change a parameter with a correction that depends on both those parameters, then click move for a parameter, should not take into account correction
# Same again but click move for all value should be taken into account