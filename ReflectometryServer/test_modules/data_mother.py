"""
Test data and classes.
"""
from mock import MagicMock

from ReflectometryServer.beamline import BeamlineMode, Beamline
from ReflectometryServer.motor_pv_wrapper import MotorPVWrapper
from ReflectometryServer.parameters import BeamlineParameter


class EmptyBeamlineParameter(BeamlineParameter):
    """
    A Bemline Parameter Stub. Counts the number of time it is asked to move
    """
    def __init__(self, name):
        super(EmptyBeamlineParameter, self).__init__(name)
        self.move_component_count = 0

    def _move_component(self):
        self.move_component_count += 1


class DataMother(object):
    """
    Test data for various tests.
    """
    BEAMLINE_MODE_NEUTRON_REFLECTION = BeamlineMode(
        "Neutron reflection",
        ["slit2height", "height", "theta", "detectorheight"])

    BEAMLINE_MODE_EMPTY = BeamlineMode("Empty", [])

    @staticmethod
    def beamline_with_3_empty_parameters():
        """

        Returns: a beamline with three empty parameters, all in a mode

        """
        one = EmptyBeamlineParameter("one")
        two = EmptyBeamlineParameter("two")
        three = EmptyBeamlineParameter("three")
        beamline_parameters = [one, two, three]
        mode = BeamlineMode("all", [beamline_parameter.name for beamline_parameter in beamline_parameters])
        naught_and_two = BeamlineMode("components1and3", [beamline_parameters[0].name, beamline_parameters[2].name])
        two = BeamlineMode("just2", [beamline_parameters[2].name])

        beamline = Beamline([], beamline_parameters, [], [mode, naught_and_two, two])

        beamline.active_mode = mode.name

        return beamline_parameters, beamline


def create_mock_axis(name, init_position, max_velocity):
    """
    Create a mock axis
    Args:
        name: pv name of axis
        init_position: initial position
        max_velocity: maximum velocity of the axis

    Returns:
            mocked axis
    """
    class MockAxis():
        def __init__(self, pv_name):
            self.name = name
            self._value = init_position
            self.max_velocity = max_velocity
            self.velocity = None
            self.after_value_change_listener = set()

        def add_after_value_change_listener(self, listener):
            self.after_value_change_listener.add(listener)

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value
            for listener in self.after_value_change_listener:
                listener(value, None, None)

    return MockAxis(name)
