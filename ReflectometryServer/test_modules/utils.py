"""
Utils for testing
"""
from math import fabs

from hamcrest.core.base_matcher import BaseMatcher

from ReflectometryServer import file_io

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


def setup_autosave(float_param_inits, bool_param_inits):
    """
    Setup the autosave to return specific values
    Args:
        float_param_inits: dictionary of autosave parameter names and there float values
        bool_param_inits:  dictionary of autosave parameter names and there bool values
    """

    def auto_save_stub_float(key, default):
        auto_save = float_param_inits
        return auto_save.get(key, default)

    def auto_save_stub_bool(key, default):
        auto_save = bool_param_inits
        return auto_save.get(key, default)

    file_io.param_float_autosave.read_parameter = auto_save_stub_float
    file_io.param_bool_autosave.read_parameter = auto_save_stub_bool


def create_parameter_with_initial_value(param_class, name, component, init_value):
    """
    Create a beamline parameter and initialise the setpoint value as would be done on start of parameter. This is done
    by faking an autosave, but could be done by calling an initalisation motor listener but that is more complicated.
    Args:
        param_class: class of parameter to create
        name: name of the parameter
        component: component this parameter is based on
        init_value: initial value

    Returns: parameter

    """
    setup_autosave({name: init_value}, {})
    return param_class(name, component, autosave=True)
