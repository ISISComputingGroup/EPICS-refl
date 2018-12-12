"""
Test data and classes.
"""
from mock import MagicMock

from ReflectometryServer.beamline import BeamlineMode, Beamline
from ReflectometryServer.components import Component, TiltingComponent, ThetaComponent
from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.ioc_driver import DisplacementDriver, AngleDriver
from ReflectometryServer.motor_pv_wrapper import MotorPVWrapper
from ReflectometryServer.movement_strategy import LinearSetup
from ReflectometryServer.parameters import BeamlineParameter, TrackingPosition, AngleParameter


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

    @staticmethod
    def beamline_s1_s3_theta_detector(spacing):
        """
        Create beamline with Slits 1 and 3 a theta and a detector
        Args:
            spacing: spacing between components

        Returns: beamline, axes

        """
        # components
        s1 = Component("s1_comp", LinearSetup(0.0, 1 * spacing, 90))
        s3 = Component("s3_comp", LinearSetup(0.0, 3 * spacing, 90))
        detector = TiltingComponent("Detector_comp", LinearSetup(0.0, 4 * spacing, 90))
        theta = ThetaComponent("ThetaComp_comp", LinearSetup(0.0, 2 * spacing, 90), [detector])
        comps = [s1, theta, s3, detector]
        # BEAMLINE PARAMETERS
        slit1_pos = TrackingPosition("s1", s1, True)
        slit3_pos = TrackingPosition("s3", s3, True)
        theta_ang = AngleParameter("theta", theta, True)
        detector_position = TrackingPosition("det", detector, True)
        detector_angle = AngleParameter("det_angle", detector, True)
        params = [slit1_pos, theta_ang, slit3_pos, detector_position, detector_angle]
        # DRIVES
        s1_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        s3_axis = create_mock_axis("MOT:MTR0102", 0, 1)
        det_axis = create_mock_axis("MOT:MTR0104", 0, 1)
        det_angle_axis = create_mock_axis("MOT:MTR0105", 0, 1)
        axes = {"s1_axis": s1_axis,
                  "s3_axis": s3_axis,
                  "det_axis": det_axis,
                  "det_angle_axis": det_angle_axis}
        drives = [DisplacementDriver(s1, s1_axis),
                  DisplacementDriver(s3, s3_axis),
                  DisplacementDriver(detector, det_axis),
                  AngleDriver(detector, det_angle_axis)]
        # MODES
        nr_inits = {}
        nr_mode = BeamlineMode("NR", [param.name for param in params], nr_inits)
        modes = [nr_mode]
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        bl = Beamline(comps, params, drives, modes, beam_start)
        bl.active_mode = nr_mode.name
        return bl, axes


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

    return MockMotorPVWrapper(name, init_position, max_velocity)


class MockMotorPVWrapper(object):
    def __init__(self, pv_name, init_position, max_velocity):
        self.name = pv_name
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
    def value(self, new_value):
        self._value = new_value
        for listener in self.after_value_change_listener:
            listener(new_value, None, None)
