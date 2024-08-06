import unittest

from hamcrest import calling, raises
from hamcrest.core import assert_that
from hamcrest.core.core import is_
from parameterized import parameterized

from ReflectometryServer import Position
from ReflectometryServer.out_of_beam import OutOfBeamLookup, OutOfBeamPosition, OutOfBeamSequence

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

        assert_that(actual.get_final_position(), is_(expected))

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

        actual, _ = lookup.out_of_beam_status(beam_intercept, displacement, None, None)  # out of been distance and parking sequence index should not mater

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
            in_beam_status, _ = lookup.out_of_beam_status(beam_intercept, position, None, None)  # only absolute position is used
            assert_that(in_beam_status, is_(expected))

    def test_GIVEN_no_positions_given_WHEN_creating_lookup_THEN_exception_thrown(self):
        positions = []

        assert_that(calling(OutOfBeamLookup).with_args(positions), raises(ValueError))

    def test_GIVEN_no_default_position_WHEN_creating_lookup_THEN_exception_thrown(self):
        positions = [OutOfBeamPosition(1, threshold=0)]

        assert_that(calling(OutOfBeamLookup).with_args(positions), raises(ValueError))

    def test_GIVEN_multiple_default_positions_WHEN_creating_lookup_THEN_exception_thrown(self):
        pos_1 = OutOfBeamPosition(1)
        pos_2 = OutOfBeamPosition(2)
        positions = [pos_1, pos_2]

        assert_that(calling(OutOfBeamLookup).with_args(positions), raises(ValueError))

    def test_GIVEN_positions_with_identical_thresholds_WHEN_creating_lookup_THEN_exception_thrown(self):
        pos_1 = OutOfBeamPosition(1, threshold=0)
        pos_2 = OutOfBeamPosition(2, threshold=0)
        positions = [pos_1, pos_2]

        assert_that(calling(OutOfBeamLookup).with_args(positions), raises(ValueError))


class TestComponentWithSequenceOutOfBeamPositions(unittest.TestCase):

    def test_GIVEN_sequence_number_is_None_WHEN_get_parking_position_THEN_last_position_in_sequence_returned(self):
        expected_value = 10
        lookup = OutOfBeamLookup([OutOfBeamSequence([0.1, expected_value])])
        beam_intercept = Position(0, 0)

        actual = lookup.get_position_for_intercept(beam_intercept).get_final_position()

        assert_that(actual, is_(expected_value))

    def test_GIVEN_sequence_of_3_WHEN_get_sequence_length_THEN_3_returned(self):
        expected_value = 3
        lookup = OutOfBeamLookup([OutOfBeamSequence([1] * expected_value)])

        actual = lookup.get_max_sequence_count()

        assert_that(actual, is_(expected_value))

    @parameterized.expand([([111, 222, 333], 0, 111), # first item
                           ([111, 222, 333], None, None), # no item so None
                           ([111, 222, 333], 1, 222), # middle item
                           ([111, 222, 333], 2, 333), # last item
                           ([111, 222, 333], 5, None), # past last item returns None
                           ([None, None, 333], 1, None),  # none is fine to return
                           ])
    def test_GIVEN_sequence_index_WHEN_get_parking_position_THEN_correct_position_in_sequence_returned_or_None(self, sequence, sequence_number, expected_value):

        lookup = OutOfBeamLookup([OutOfBeamSequence(sequence)])
        beam_intercept = Position(0, 0)

        actual = lookup.get_position_for_intercept(beam_intercept).get_sequence_position(sequence_number)

        assert_that(actual, is_(expected_value))


    @parameterized.expand([([1, 2, 3, 4], 0, 1 + 0.1, True),  # within tolerance of sequence end
                           ([1, 2, 3, 4], 1, 1 + 0.1, False),  # within tolerance of first sequence end but not current end
                           ([1, 2, 3, 4], 0, 1 + 0.3, False),  # out of tolerance
                           ([1, 2, 3, 4], None, 4, True),  # sequence index is none so it is at the end of the current sequence
                           ([None, None, 3, 4], 1, 4, True),  # sequence position is None
                           ([None, None, 3, 4], 4, 4, True),  # sequence index is greater than sequence length
            ])
    def test_GIVEN_positions_with_tolerance_WHEN_checking_whether_component_is_at_end_of_sequence_THEN_returns_correct_status(self, sequence, parking_index, position, expected):
        tolerance = 0.2
        lookup = OutOfBeamLookup([OutOfBeamSequence(sequence, tolerance=tolerance)])


        _, result = lookup.out_of_beam_status(Position(0, 0), position, None, parking_index=parking_index)  # only absolute position is used
        assert_that(result, is_(expected))

    def test_GIVEN_sequence_positions_ending_in_none_WHEN_creating_lookup_THEN_exception_thrown(self):
        positions = [1, None]

        assert_that(calling(OutOfBeamSequence).with_args(positions), raises(ValueError))

    def test_GIVEN_sequence_positions_with_none_between_values_WHEN_creating_lookup_THEN_exception_thrown(self):
        positions = [1, None, 2]

        assert_that(calling(OutOfBeamSequence).with_args(positions), raises(ValueError))
