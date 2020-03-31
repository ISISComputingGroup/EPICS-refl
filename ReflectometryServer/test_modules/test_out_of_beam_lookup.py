import unittest

from hamcrest.core import assert_that
from hamcrest.core.core import is_
from parameterized import parameterized

from ReflectometryServer import Position
from ReflectometryServer.out_of_beam import OutOfBeamPosition, OutOfBeamLookup

PARK_HIGH_POS = 10
PARK_HIHI_POS = 20
PARK_LOW_POS = -10


class TestComponentWithOutOfBeamPositions(unittest.TestCase):
    park_high = OutOfBeamPosition(PARK_HIGH_POS)
    park_hihi = OutOfBeamPosition(PARK_HIHI_POS, threshold=0)
    park_low = OutOfBeamPosition(PARK_LOW_POS, threshold=15)

    def setUp(self):
        self.positions = [self.park_high, self.park_low, self.park_hihi]

    @parameterized.expand([(-5, PARK_HIGH_POS), (0, PARK_HIHI_POS), (50, PARK_LOW_POS)])
    def test_GIVEN_multiple_out_of_beam_position_WHEN_getting_position_for_given_intercept_THEN_correct_position_returned(self, beam_height, expected):
        lookup = OutOfBeamLookup(self.positions)
        beam_intercept = Position(beam_height, 0)

        actual = lookup.get_position_for_intercept(beam_intercept)

        assert_that(actual.position, is_(expected))

    @parameterized.expand([(-5, PARK_LOW_POS, True),
                           (-5, PARK_HIGH_POS, False),
                           (-5, PARK_HIHI_POS, True),
                           (0, PARK_LOW_POS, True),
                           (0, PARK_HIGH_POS, True),
                           (0, PARK_HIHI_POS, False),
                           (20, PARK_LOW_POS, False),
                           (20, PARK_HIGH_POS, True),
                           (20, PARK_HIHI_POS, True),
                           ])
    def test_GIVEN_multiple_out_of_beam_positions_WHEN_checking_whether_component_is_in_beam_THEN_lookup_provides_correct_answer_for_given_beam_intersect(
            self, beam_height, displacement, expected):
        lookup = OutOfBeamLookup(self.positions)
        beam_intercept = Position(beam_height, 0)

        actual = lookup.is_in_beam(beam_intercept, displacement)

        assert_that(actual, is_(expected))

    # test for a range of values
    @parameterized.expand([(-5, PARK_LOW_POS),
                           (-5, PARK_HIGH_POS),
                           (-5, PARK_HIHI_POS),
                           (0, PARK_LOW_POS),
                           (0, PARK_HIGH_POS),
                           (0, PARK_HIHI_POS),
                           (20, PARK_LOW_POS),
                           (20, PARK_HIGH_POS),
                           (20, PARK_HIHI_POS),
                           ])
    def test_GIVEN_no_out_of_beam_position_WHEN_checking_whether_component_is_in_beam_THEN_returns_true(self, beam_height, displacement):
        expected = True
        lookup = OutOfBeamLookup([])
        beam_intercept = Position(beam_height, 0)

        actual = lookup.is_in_beam(beam_height, displacement)

        assert_that(actual, is_(expected))

    @parameterized.expand([(PARK_LOW_POS, 0.5, False),
                           (PARK_LOW_POS, 2, True),
                           (PARK_LOW_POS, 4, True),
                           (PARK_HIGH_POS, 0.5, False),
                           (PARK_HIGH_POS, 2, False),
                           (PARK_HIGH_POS, 4, True),])
    def test_GIVEN_positions_with_tolerance_WHEN_checking_whether_component_is_in_beam_THEN_returns_correct_status_for_each_position(self, position_to_check, offset_from_pos, expected):
        beam_intercept = Position(0, 0)
        if position_to_check is PARK_HIGH_POS:
            beam_intercept = Position(2, 0)
        tolerance_low = 0.5
        tolerance_high = 2
        park_low_with_tolerance = OutOfBeamPosition(PARK_LOW_POS, tolerance=tolerance_low)
        park_high_with_tolerance = OutOfBeamPosition(PARK_HIGH_POS, threshold=1, tolerance=tolerance_high)

        lookup = OutOfBeamLookup([park_low_with_tolerance, park_high_with_tolerance])

        for position in [position_to_check + offset_from_pos, position_to_check - offset_from_pos]:
            in_beam_status = lookup.is_in_beam(beam_intercept, position)
            assert_that(in_beam_status, is_(expected))
