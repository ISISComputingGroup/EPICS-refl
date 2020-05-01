"""
SimpleObservable data and classes.
"""
from math import tan, radians, sin, cos

from mock import Mock

from ReflectometryServer import GridDataFileReader, InterpolateGridDataCorrectionFromProvider
from ReflectometryServer.pv_wrapper import DEFAULT_SCALE_FACTOR
from ReflectometryServer.pv_wrapper import SetpointUpdate, ReadbackUpdate, IsChangingUpdate
from server_common.observable import observable
from utils import DEFAULT_TEST_TOLERANCE

from ReflectometryServer.beamline import BeamlineMode, Beamline
from ReflectometryServer.components import Component, TiltingComponent, ThetaComponent, ReflectingComponent
from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.ioc_driver import DisplacementDriver, AngleDriver
from ReflectometryServer.parameters import BeamlineParameter, TrackingPosition, AngleParameter, DirectParameter, \
    SlitGapParameter
import numpy as np


class EmptyBeamlineParameter(BeamlineParameter):
    """
    A Bemline Parameter Stub. Counts the number of time it is asked to move
    """

    def _initialise_sp_from_file(self):
        pass

    def _initialise_sp_from_motor(self, _):
        pass

    def _set_changed_flag(self):
        pass

    def _move_component(self):
        pass

    def _rbv(self):
        pass

    def __init__(self, name):
        super(EmptyBeamlineParameter, self).__init__(name)
        self.move_component_count = 0

    def _check_and_move_component(self):
        self.move_component_count += 1

    def validate(self, drivers):
        return []


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
    def beamline_s1_s3_theta_detector(spacing, initilise_mode_nr=True):
        """
        Create beamline with Slits 1 and 3 a theta and a detector
        Args:
            spacing: spacing between components

        Returns: beamline, axes

        """
        # COMPONENTS
        s1 = Component("s1_comp", PositionAndAngle(0.0, 1 * spacing, 90))
        s3 = Component("s3_comp", PositionAndAngle(0.0, 3 * spacing, 90))
        detector = TiltingComponent("Detector_comp", PositionAndAngle(0.0, 4 * spacing, 90))
        theta = ThetaComponent("ThetaComp_comp", PositionAndAngle(0.0, 2 * spacing, 90), [detector])
        comps = [s1, theta, s3, detector]

        # BEAMLINE PARAMETERS
        slit1_pos = TrackingPosition("s1", s1, True)
        slit3_pos = TrackingPosition("s3", s3, True)
        theta_ang = AngleParameter("theta", theta, True)
        detector_position = TrackingPosition("det", detector, True)
        detector_angle = AngleParameter("det_angle", detector, True)
        params = [slit1_pos, theta_ang, slit3_pos, detector_position, detector_angle]

        # DRIVERS
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
        disabled_mode = BeamlineMode("DISABLED", [param.name for param in params], nr_inits, is_disabled=True)
        modes = [nr_mode, disabled_mode]
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        bl = Beamline(comps, params, drives, modes, beam_start)
        if initilise_mode_nr:
            bl.active_mode = nr_mode.name
        return bl, axes

    @staticmethod
    def beamline_s1_gap_theta_s3_gap_detector(spacing):
        """
        Create beamline with Slits 1 and 3 a theta and a detector
        Args:
            spacing: spacing between components

        Returns: beamline, axes

        """
        # DRIVERS
        s1_gap_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        s3_gap_axis = create_mock_axis("MOT:MTR0103", 0, 1)
        axes = {"s1_gap_axis": s1_gap_axis}
        drives = []

        # COMPONENTS
        detector = TiltingComponent("Detector_comp", PositionAndAngle(0.0, 4 * spacing, 90))
        theta = ThetaComponent("ThetaComp_comp", PositionAndAngle(0.0, 2 * spacing, 90), [detector])
        comps = [theta]

        # BEAMLINE PARAMETERS
        s1_gap = SlitGapParameter("s1_gap", s1_gap_axis, sim=True)
        theta_ang = AngleParameter("theta", theta, sim=True)
        s3_gap = SlitGapParameter("s3_gap", s3_gap_axis, sim=True)
        detector_position = TrackingPosition("det", detector, sim=True)
        detector_angle = AngleParameter("det_angle", detector, sim=True)
        params = [s1_gap, theta_ang, s3_gap, detector_position, detector_angle]

        # MODES
        nr_inits = {}
        nr_mode = [BeamlineMode("NR", [param.name for param in params], nr_inits)]
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        bl = Beamline(comps, params, drives, nr_mode, beam_start)

        return bl, axes

    @staticmethod
    def beamline_sm_theta_detector(sm_angle, theta, det_offset=0, autosave_theta_not_offset=True, beam_angle=0.0, sm_angle_engineering_correction=False):
        """
        Create beamline with supermirror, theta and a tilting detector.

        Args:
            sm_angle (float): The initialisation value for supermirror angle
            theta (float): The initialisation value for theta
            det_offset (float): The initialisation value for detector offset
            autosave_theta_not_offset (bool): true to autosave theta and not the offset, false otherwise
            beam_angle (float): angle of the beam, worked out as the angle the components run along + 90

        Returns: beamline, axes
        """
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        perp_to_floor_angle_in_mantid = 90 + beam_angle

        # COMPONENTS
        z_sm_to_sample = 1
        z_sample_to_det = 2
        sm_comp = ReflectingComponent("sm_comp", PositionAndAngle(0.0, 0, perp_to_floor_angle_in_mantid))
        detector_comp = TiltingComponent("detector_comp", PositionAndAngle(0.0, z_sm_to_sample + z_sample_to_det, perp_to_floor_angle_in_mantid))
        theta_comp = ThetaComponent("theta_comp", PositionAndAngle(0.0, z_sm_to_sample, perp_to_floor_angle_in_mantid), [detector_comp])

        comps = [sm_comp, theta_comp, detector_comp]

        # BEAMLINE PARAMETERS
        sm_angle_param = AngleParameter("sm_angle", sm_comp)
        theta_param = AngleParameter("theta", theta_comp, autosave=autosave_theta_not_offset)
        detector_position_param = TrackingPosition("det_pos", detector_comp, autosave=not autosave_theta_not_offset)
        detector_angle_param = AngleParameter("det_angle", detector_comp)

        params = [sm_angle_param, theta_param, detector_position_param, detector_angle_param]

        # DRIVERS
        # engineering correction
        if sm_angle_engineering_correction:
            grid_data_provider = GridDataFileReader("linear_theta")
            grid_data_provider.variables = ["Theta"]
            grid_data_provider.points = np.array([[-90, ], [0.0, ], [90.0, ]])
            grid_data_provider.corrections = np.array([-45, 0.0, 45])
            grid_data_provider.read = lambda: None
            correction = InterpolateGridDataCorrectionFromProvider(grid_data_provider, theta_param)
            size_of_correction = theta / 2.0
        else:
            correction = None
            size_of_correction = 0

        # setup motors
        beam_angle_after_sample = theta * 2 + sm_angle * 2
        supermirror_segment = (z_sm_to_sample, sm_angle)
        theta_segment = (z_sample_to_det, theta)
        reflection_offset = DataMother._calc_reflection_offset(beam_angle, [supermirror_segment, theta_segment])
        sm_axis = create_mock_axis("MOT:MTR0101", sm_angle + size_of_correction, 1)
        det_axis = create_mock_axis("MOT:MTR0104", reflection_offset + det_offset, 1)
        det_angle_axis = create_mock_axis("MOT:MTR0105",  beam_start.angle + beam_angle_after_sample, 1)

        axes = {"sm_axis": sm_axis,
                "det_axis": det_axis,
                "det_angle_axis": det_angle_axis}

        drives = [AngleDriver(sm_comp, sm_axis, engineering_correction=correction),
                  DisplacementDriver(detector_comp, det_axis),
                  AngleDriver(detector_comp, det_angle_axis)]

        # MODES
        nr_inits = {}
        nr_mode = BeamlineMode("NR", [param.name for param in params], nr_inits)
        modes = [nr_mode]
        beam_start = PositionAndAngle(0.0, 0.0, 0.0)
        bl = Beamline(comps, params, drives, modes, beam_start)
        bl.active_mode = nr_mode.name
        return bl, axes

    @staticmethod
    def _calc_reflection_offset(beam_angle, segments):
        """
        Calculates a position offset to the beam intercept for a linear axis given an ordered list of beam segments,
        each of which adds an angle to the beam.

        Params:
            beam_angle (float): The angle of the straight through beam to the linear motion axes
            segments (tuple[float, float]): A list of beam segments made of tuples with (segment_length, added angle)

        Returns: The total offset for the linear axis
        """
        total_offset = 0.0

        reflection_angles = []
        for distance, added_angle in segments:
            reflection_angles.append(added_angle)

            cumulative_reflection_angle = 0
            for reflection_angle in reflection_angles:
                cumulative_reflection_angle += 2*reflection_angle

            offset_1 = distance * sin(radians(beam_angle))
            offset_2 = distance * cos(radians(beam_angle)) * tan(radians(cumulative_reflection_angle - beam_angle))
            total_offset += offset_1 + offset_2

        return total_offset


def create_mock_axis(name, init_position, max_velocity, backlash_distance=0, backlash_velocity=1, direction="Pos"):
    """
    Create a mock axis
    Args:
        name: pv name of axis
        init_position: initial position
        max_velocity: maximum velocity of the axis
        backlash_distance: distance that the axis will backlash
        backlash_velocity: velocity that the backlash is performed
        direction: calibration direction of the axis, Pos or Neg
    Returns:
            mocked axis
    """

    return MockMotorPVWrapper(name, init_position, max_velocity, True, backlash_distance, backlash_velocity, direction)


@observable(SetpointUpdate, ReadbackUpdate, IsChangingUpdate)
class MockMotorPVWrapper(object):
    def __init__(self, pv_name, init_position, max_velocity, is_vertical=True, backlash_distance=0, backlash_velocity=1, direction="Neg"):
        self.name = pv_name
        self._value = init_position
        self.max_velocity = max_velocity
        self.min_velocity = max_velocity / DEFAULT_SCALE_FACTOR
        self.velocity = None
        self.direction = direction
        self.backlash_distance = backlash_distance
        if self.direction == "Pos":
            self.backlash_distance = backlash_distance * -1
        self.backlash_velocity = backlash_velocity
        self.resolution = DEFAULT_TEST_TOLERANCE
        self.after_status_change_listener = set()
        self.after_velocity_change_listener = set()
        self.is_vertical = is_vertical
        self.set_position_as_value = None
        self._last_set_point_set = None

    def initialise(self):
        pass

    def add_after_status_change_listener(self, listener):
        self.after_status_change_listener.add(listener)

    def add_after_velocity_change_listener(self, listener):
        self.after_velocity_change_listener.add(listener)

    def initiate_move_with_change_of_velocity(self):
        pass

    def cache_velocity(self):
        pass

    def restore_velocity(self):
        pass

    @property
    def sp(self):
        return self._value

    @sp.setter
    def sp(self, new_value):
        self._last_set_point_set = new_value
        self._value = new_value
        self.trigger_listeners(SetpointUpdate(new_value, None, None))
        self.trigger_listeners(ReadbackUpdate(new_value, None, None))

    def trigger_rbv_change(self):
        self.trigger_listeners(ReadbackUpdate(self._value, None, None))

    @property
    def rbv(self):
        return self._value

    def define_position_as(self, new_value):
        self.set_position_as_value = new_value
        self._value = new_value
        self.trigger_listeners(SetpointUpdate(new_value, None, None))
        self.trigger_listeners(ReadbackUpdate(new_value, None, None))


class MockChannelAccess(object):
    def __init__(self, pvs):
        self._pvs = pvs

    def pv_exists(self, pv):
        return pv in self._pvs.keys()

    def add_monitor(self,pv, call_back_function):
        pass

    def caget(self, pv):
        try:
            return self._pvs[pv]
        except KeyError:
            return None

    def caput(self, pv, value):
        self._pvs[pv] = value


def create_mock_JawsCentrePVWrapper(name, init_position, max_velocity, backlash_distance=0, backlash_velocity=1, direction="Pos"):
    """
    Create a mock jaws centre pv wrapper for testing
    Returns: mock
    """

    mock_jaws_wrapper = create_mock_axis(name, init_position, max_velocity, backlash_distance, backlash_velocity, direction)
    mock_jaws_wrapper.define_position_as = Mock()
    mock_jaws_wrapper.is_vertical = False

    return mock_jaws_wrapper

