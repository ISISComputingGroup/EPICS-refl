import unittest

from hamcrest import *
from mock import Mock, patch
from parameterized import parameterized

from ReflectometryServer.footprint_calc import *

INTER_SLIT1_POS = 0
INTER_SLIT2_POS = 1923
INTER_SAMPLE_POS = 2287
INTER_SLIT3_POS = 3007.5
INTER_SLIT4_POS = 4986.5
INTER_LAMBDA_MIN = 2
INTER_LAMBDA_MAX = 17

DEFAULT_GAPS = {S1_ID: 40, S2_ID: 30, S3_ID: 30, S4_ID: 40, SA_ID: 200}

TEST_TOLERANCE = 1e-5


class TestFootprintCalc(unittest.TestCase):
    """
    Test the output of the beam footprint calculator. Verifies the results against values from the spreadsheet the
    scientists used previously.
    """

    @staticmethod
    def set_up_slit(value):
        slit = Mock()
        slit.sp = float(value)
        slit.sp_rbv = float(value)
        slit.rbv = float(value)
        return slit

    def setUp(self):
        default_theta = 0.25
        self.theta = Mock()
        self.theta.sp_rbv = default_theta
        self.theta.sp = default_theta
        self.theta.rbv = default_theta

        self.calc_setup = FootprintSetup(
            INTER_SLIT1_POS,
            INTER_SLIT2_POS,
            INTER_SLIT3_POS,
            INTER_SLIT4_POS,
            INTER_SAMPLE_POS,
            self.set_up_slit(40),
            self.set_up_slit(30),
            self.set_up_slit(30),
            self.set_up_slit(40),
            self.theta,
            INTER_LAMBDA_MIN,
            INTER_LAMBDA_MAX,
        )

        self.calc = FootprintCalculatorSetpointReadback(self.calc_setup)

        for key, value in DEFAULT_GAPS.items():
            self.calc.gaps[key] = value

    def test_GIVEN_two_components_WHEN_calculating_distance_THEN_distance_is_correct(self):
        pos1 = S2_ID
        pos2 = S4_ID
        expected = INTER_SLIT4_POS - INTER_SLIT2_POS

        actual = self.calc.distance(pos1, pos2)

        self.assertEqual(expected, actual)

    def test_GIVEN_two_components_in_reverse_order_WHEN_calculating_distance_THEN_distance_is_correct(
        self,
    ):
        pos1 = S2_ID
        pos2 = S4_ID
        expected = INTER_SLIT4_POS - INTER_SLIT2_POS

        actual = self.calc.distance(pos2, pos1)

        self.assertEqual(expected, actual)

    @parameterized.expand(
        [
            (0, 0),
            (0.1, 0.349065673),
            (0.5, 1.7453071),
            (1.0, 3.490481287),
            (10, 34.72963553),
            (45, 141.4213562),
            (90, 200),
            (135, 141.4213562),
        ]
    )
    def test_GIVEN_fixed_sample_size_and_variable_theta_value_WHEN_calculating_equivalent_slit_size_of_sample_THEN_result_is_correct(
        self, theta, expected
    ):
        self.theta.sp_rbv = theta
        actual = self.calc.calc_equivalent_gap_by_sample_size()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    @parameterized.expand(
        [
            (10, 0.043633093),
            (50, 0.218165464),
            (100, 0.436330928),
            (200, 0.872661857),
            (500, 2.181654642),
        ]
    )
    def test_GIVEN_variable_sample_size_and_fixed_theta_value_WHEN_calculating_equivalent_slit_size_of_sample_THEN_result_is_correct(
        self, sample_size, expected
    ):
        self.calc.gaps[SA_ID] = sample_size

        actual = self.calc.calc_equivalent_gap_by_sample_size()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_INTER_parameters_WHEN_calculating_equivalent_slit_of_penumbra_at_sample_THEN_result_is_correct(
        self,
    ):
        expected = 43.25013001

        actual = self.calc.calc_equivalent_gap_by_penumbra()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    @parameterized.expand(
        [
            (0.1, 24780.51171),
            (0.5, 4956.162731),
            (1.0, 2478.175727),
            (10, 249.0675721),
            (45, 61.16492043),
            (90, 43.25013001),
            (135, 61.16492043),
        ]
    )
    def test_GIVEN_variable_theta_value_WHEN_calculating_penumbra_footprint_at_sample_THEN_result_is_correct(
        self, theta, expected
    ):
        self.theta.sp_rbv = theta
        actual = self.calc.calc_footprint()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_sample_size_smaller_than_penumbra_size_WHEN_getting_slit_gap_equivalent_to_sample_THEN_return_sample_size_value(
        self,
    ):
        penumbra_size = 300

        with patch.object(
            self.calc, "calc_equivalent_gap_by_sample_size"
        ) as mock_sample, patch.object(
            self.calc, "calc_equivalent_gap_by_penumbra"
        ) as mock_sample_penumbra, patch.object(
            self.calc, "calc_footprint", return_value=penumbra_size
        ):
            self.calc.get_sample_slit_gap_equivalent()

            mock_sample_penumbra.assert_not_called()
            mock_sample.assert_called_once()

    def test_GIVEN_penumbra_size_smaller_than_sample_size_WHEN_getting_slit_gap_equivalent_to_sample_THEN_return_sample_penumbra_value(
        self,
    ):
        penumbra_size = 100

        with patch.object(
            self.calc, "calc_equivalent_gap_by_sample_size"
        ) as mock_sample, patch.object(
            self.calc, "calc_equivalent_gap_by_penumbra"
        ) as mock_sample_penumbra, patch.object(
            self.calc, "calc_footprint", return_value=penumbra_size
        ):
            self.calc.get_sample_slit_gap_equivalent()

            mock_sample.assert_not_called()
            mock_sample_penumbra.assert_called_once()

    @parameterized.expand(
        [
            (S1_ID, S2_ID, 416.9432188),
            (S1_ID, SA_ID, 204.7719181),
            (S1_ID, S3_ID, 266.6636815),
            (S1_ID, S4_ID, 183.825933),
            (S2_ID, SA_ID, 969.5817187),
            (S2_ID, S3_ID, 633.3285232),
            (S2_ID, S4_ID, 261.790849),
            (SA_ID, S3_ID, 490.7094045),
            (SA_ID, S4_ID, 173.4867372),
            (S3_ID, S4_ID, 405.1548997),
        ]
    )
    def test_GIVEN_beam_segment_WHEN_calculating_resolution_THEN_result_is_correct(
        self, comp1, comp2, expected
    ):
        actual = self.calc.calc_resolution(comp1, comp2)

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    def test_GIVEN_a_theta_value_WHEN_calculating_minimum_resolution_of_all_beamline_segments_THEN_result_is_minimum(
        self,
    ):
        expected = 173.4867372

        actual = self.calc.calc_min_resolution()

        assert_that(actual, is_(close_to(expected, TEST_TOLERANCE)))

    @parameterized.expand(
        [
            (0.1, 0.001290144, 0.010966222),
            (0.5, 0.00645064, 0.05483044),
            (1.0, 0.012900789, 0.109656704),
            (10, 0.128360433, 1.091063679),
            (45, 0.52269211, 4.442882938),
            (90, 0.739198271, 6.283185307),
            (135, 0.52269211, 4.442882938),
        ]
    )
    def test_GIVEN_variable_theta_WHEN_calculating_Q_range_THEN_returns_correct_range(
        self, theta, qmin_expected, qmax_expected
    ):
        self.theta.sp_rbv = theta

        qmin_actual = self.calc.calc_q_min()
        qmax_actual = self.calc.calc_q_max()

        assert_that(qmin_actual, is_(close_to(qmin_expected, TEST_TOLERANCE)))
        assert_that(qmax_actual, is_(close_to(qmax_expected, TEST_TOLERANCE)))


if __name__ == "__main__":
    unittest.main()
