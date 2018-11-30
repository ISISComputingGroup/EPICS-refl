import unittest

from math import tan, radians, sqrt, trunc
from hamcrest import *
from mock import patch, mock
from parameterized import parameterized

from ReflectometryServer.footprint_calc import *

INTER_SLIT1_POS = 0
INTER_SLIT2_POS = 1923
INTER_SAMPLE_POS = 2287
INTER_SLIT3_POS = 3007.5
INTER_SLIT4_POS = 4986.5

DEFAULT_GAPS = {S1: 40,
                S2: 30,
                S3: 30,
                S4: 40,
                SA: 200}

TEST_TOLERANCE = 1e-5


class TestFootprintCalc(unittest.TestCase):
    """
    Test the output of the beam footprint calculator. Verifies the code against values from the excel spreadsheet the
    scientists previously used.
    """

    def setUp(self):
        self.calc = FootprintCalculator(INTER_SLIT1_POS,
                                        INTER_SLIT2_POS,
                                        INTER_SLIT3_POS,
                                        INTER_SLIT4_POS,
                                        INTER_SAMPLE_POS)

        for key, value in DEFAULT_GAPS.iteritems():
            self.calc.set_gap(key, value)

    def test_GIVEN_initial_values_as_int_WHEN_setting_up_footprint_calculator_THEN_all_values_are_converted_to_float(self):
        for value in self.calc.gaps.values():
            assert_that(value, is_(float))
        for value in self.calc.positions.values():
            assert_that(value, is_(float))

    def test_GIVEN_two_components_WHEN_calculating_distance_THEN_distance_is_correct(self):
        pos1 = S2
        pos2 = S4
        expected = INTER_SLIT4_POS - INTER_SLIT2_POS

        actual = self.calc.distance(pos1, pos2)

        self.assertEqual(expected, actual)

    def test_GIVEN_two_components_in_reverse_order_WHEN_calculating_distance_THEN_distance_is_correct(self):
        pos1 = S2
        pos2 = S4
        expected = INTER_SLIT4_POS - INTER_SLIT2_POS

        actual = self.calc.distance(pos2, pos1)

        self.assertEqual(expected, actual)

    @parameterized.expand([(0, 0),
                           (0.1, 0.349065673),
                           (0.5, 1.7453071),
                           (1.0, 3.490481287),
                           (10, 34.72963553),
                           (45, 141.4213562),
                           (90, 200),
                           (135, 141.4213562)])
    def test_GIVEN_fixed_sample_size_and_variable_theta_value_WHEN_calculating_equivalent_slit_size_of_sample_THEN_result_is_correct(self, theta, expected):
        actual = self.calc.calc_equivalent_gap_by_sample_size(theta)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    @parameterized.expand([(10, 0.043633093),
                           (50, 0.218165464),
                           (100, 0.436330928),
                           (200, 0.872661857),
                           (500, 2.181654642)])
    def test_GIVEN_variable_sample_size_and_fixed_theta_value_WHEN_calculating_equivalent_slit_size_of_sample_THEN_result_is_correct(self, sample_size, expected):
        theta = 0.25
        self.calc.set_gap(SA, sample_size)

        actual = self.calc.calc_equivalent_gap_by_sample_size(theta)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_INTER_parameters_WHEN_calculating_equivalent_slit_of_penumbra_at_sample_THEN_result_is_correct(self):
        expected = 43.25013001

        actual = self.calc.calc_equivalent_gap_by_penumbra()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    @parameterized.expand([(0.1, 24780.51171),
                           (0.5, 4956.162731),
                           (1.0, 2478.175727),
                           (10, 249.0675721),
                           (45, 61.16492043),
                           (90, 43.25013001),
                           (135, 61.16492043)])
    def test_GIVEN_variable_theta_value_WHEN_calculating_penumbra_at_sample_THEN_result_is_correct(self, theta, expected):
        actual = self.calc.calc_penumbra(theta)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_sample_size_smaller_than_penumbra_size_WHEN_getting_slit_gap_equivalent_to_sample_THEN_return_sample_size_value(self):
        theta = 0.25
        penumbra_size = 300

        with patch.object(self.calc, 'calc_equivalent_gap_by_sample_size') as mock_sample, \
                patch.object(self.calc, 'calc_equivalent_gap_by_penumbra') as mock_sample_penumbra, \
                patch.object(self.calc, 'calc_penumbra', return_value=penumbra_size):
            self.calc.get_sample_slit_gap_equivalent(theta)

            mock_sample_penumbra.assert_not_called()
            mock_sample.assert_called_once()

    def test_GIVEN_penumbra_size_smaller_than_sample_size_WHEN_getting_slit_gap_equivalent_to_sample_THEN_return_sample_penumbra_value(self):
        theta = 0.25
        penumbra_size = 100

        with patch.object(self.calc, 'calc_equivalent_gap_by_sample_size') as mock_sample, \
                patch.object(self.calc, 'calc_equivalent_gap_by_penumbra') as mock_sample_penumbra, \
                patch.object(self.calc, 'calc_penumbra', return_value=penumbra_size):
            self.calc.get_sample_slit_gap_equivalent(theta)

            mock_sample.assert_not_called()
            mock_sample_penumbra.assert_called_once()

    @parameterized.expand([(S1, S2, 416.9432188),
                           (S1, SA, 204.7719181),
                           (S1, S3, 266.6636815),
                           (S1, S4, 183.825933),
                           (S2, SA, 969.5817187),
                           (S2, S3, 633.3285232),
                           (S2, S4, 261.790849),
                           (SA, S3, 490.7094045),
                           (SA, S4, 173.4867372),
                           (S3, S4, 405.1548997)])
    def test_GIVEN_beam_segment_WHEN_calculating_resolution_THEN_result_is_correct(self, comp1, comp2, expected):
        theta = 0.25

        actual = self.calc.calc_resolution(comp1, comp2, theta)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_a_theta_value_WHEN_calculating_minimum_resolution_of_all_beamline_segments_THEN_result_is_minimum(self):
        theta = 0.25
        expected = 173.4867372

        actual = self.calc.calc_min_resolution(theta)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_calculate_right_footprint(self):
        pass

if __name__ == '__main__':
    unittest.main()
