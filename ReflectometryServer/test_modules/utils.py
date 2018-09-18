"""
Utils for testing
"""
from math import fabs

from hamcrest.core.base_matcher import BaseMatcher

DEFAULT_TEST_TOLERANCE = 1e-9


class IsPositionAndAngle(BaseMatcher):
    """
    Matcher for the beam object

    Checks that the beam values are all the same
    """
    def __init__(self, expected_beam, do_compare_angle, tolerance=None):
        self.expected_position_and_angle = expected_beam
        self.compare_angle = do_compare_angle
        if tolerance is None:
            self._tolerance = DEFAULT_TEST_TOLERANCE
        else:
            self._tolerance = tolerance

    def _matches(self, beam):
        """
        Does the beam given match the expected beam
        :param beam: beam given
        :return: True if it matches; False otherwise
        """
        if not hasattr(beam, 'z') or not hasattr(beam, 'y') or (self.compare_angle and not hasattr(beam, 'angle')):
            return False
        return fabs(beam.z - self.expected_position_and_angle.z) <= self._tolerance and \
            fabs(beam.y - self.expected_position_and_angle.y) <= self._tolerance and \
               (not self.compare_angle or fabs(beam.angle - self.expected_position_and_angle.angle) <= self._tolerance)

    def describe_to(self, description):
        """
        Describes the problem with the match.
        :param description: description to add problem with
        """
        if self.compare_angle:
            description.append_text(self.expected_position_and_angle)
        else:
            description.append_text("{} (compare position to within {})".format(self.expected_position_and_angle,
                                                                                self._tolerance))


def position_and_angle(expected_beam, tolerance=None):
    """
    PositionAndAngle matcher.
    Args:
        expected_beam: expected beam to match.
        tolerance: tolerance within which the number need to be

    Returns: the matcher for the beam

    """
    return IsPositionAndAngle(expected_beam, True, tolerance)


def position(expected_position, tolerance=None):
    """
    Position matcher.
    Args:
        expected_position: expected position to match.
        tolerance: tolerance within which the number need to be

    Returns: the matcher for the position

    """
    return IsPositionAndAngle(expected_position, False, tolerance)