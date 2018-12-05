import unittest

from math import tan, radians
from hamcrest import *
from mock import Mock

from ReflectometryServer.components import ReflectingComponent, Component, TiltingComponent, ThetaComponent
from ReflectometryServer.ioc_driver import DisplacementDriver, AngleDriver
from ReflectometryServer.movement_strategy import LinearSetup
from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.parameters import TrackingPosition, AngleParameter
from ReflectometryServer.test_modules.data_mother import DataMother, create_mock_axis
from utils import position_and_angle
from ReflectometryServer.motor_pv_wrapper import AlarmSeverity, AlarmStatus, MotorPVWrapper




class TestComponentBeamline(unittest.TestCase):

    def setup_beamline(self, initial_mirror_angle, mirror_position, beam_start):
        jaws = Component("jaws", setup=LinearSetup(0, 0, 90))
        mirror = ReflectingComponent("mirror", setup=LinearSetup(0, mirror_position, 90))
        mirror.beam_path_set_point.angle = initial_mirror_angle
        jaws3 = Component("jaws3", setup=LinearSetup(0, 20, 90))
        beamline = Beamline([jaws, mirror, jaws3], [], [], [], beam_start)
        return beamline, mirror

    def test_GIVEN_beam_line_contains_one_passive_component_WHEN_beam_set_THEN_component_has_beam_out_same_as_beam_in(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("jaws", setup=LinearSetup(0, 2, 90))
        beamline = Beamline([jaws], [], [], [], beam_start)

        result = beamline[0].beam_path_set_point.get_outgoing_beam()

        assert_that(result, is_(position_and_angle(beam_start)))

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_beam_set_THEN_each_component_has_beam_out_which_is_effected_by_each_component_in_turn(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 45
        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)
        bounced_beam = PositionAndAngle(y=0, z=mirror_position, angle=initial_mirror_angle * 2)
        expected_beams = [beam_start, bounced_beam, bounced_beam]

        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component {}".format(index))


    def test_GIVEN_beam_line_contains_multiple_component_WHEN_angle_on_mirror_changed_THEN_beam_positions_are_all_recalculated(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 0

        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)

        mirror_final_angle = 45
        bounced_beam = PositionAndAngle(y=0, z=mirror_position, angle=mirror_final_angle * 2)
        expected_beams = [beam_start, bounced_beam, bounced_beam]

        mirror.beam_path_set_point.angle = mirror_final_angle
        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component index {}".format(index))

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_mirror_disabled_THEN_beam_positions_are_all_recalculated(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        mirror_position = 10
        initial_mirror_angle = 45

        beamline, mirror = self.setup_beamline(initial_mirror_angle, mirror_position, beam_start)
        expected_beams = [beam_start, beam_start, beam_start]

        mirror.beam_path_set_point.enabled = False
        results = [component.beam_path_set_point.get_outgoing_beam() for component in beamline]

        for index, (result, expected_beam) in enumerate(zip(results, expected_beams)):
            assert_that(result, position_and_angle(expected_beam), "in component index {}".format(index))


class TestComponentBeamlineReadbacks(unittest.TestCase):

    def test_GIVEN_components_in_beamline_WHEN_readback_changed_THEN_components_after_changed_component_updatereadbacks(self):
        comp1 = Component("comp1", LinearSetup(0, 1, 90))
        comp2 = Component("comp2", LinearSetup(0, 2, 90))
        beamline = Beamline([comp1, comp2], [], [], [DataMother.BEAMLINE_MODE_EMPTY])

        callback = Mock()
        comp2.beam_path_rbv.set_incoming_beam = callback
        comp1.beam_path_rbv.set_displacement(1.0, AlarmSeverity.No, AlarmStatus.No)

        assert_that(callback.called, is_(True))


class TestRealistic(unittest.TestCase):

    def test_GIVEN_weird_WHEN_seup_HEN_ok(self):
        SPACING = 2.0

        # components
        s1 = Component("s1", LinearSetup(0.0, 1*SPACING, 90))
        s3 = Component("s3", LinearSetup(0.0, 3*SPACING, 90))
        detector = TiltingComponent("Detector", LinearSetup(0.0, 4*SPACING, 90))
        theta = ThetaComponent("ThetaComp", LinearSetup(0.0, 2*SPACING, 90), [detector])
        comps = [s1, theta, s3, detector]

        # BEAMLINE PARAMETERS
        slit1_pos = TrackingPosition("s1_pos", s1, True)
        slit3_pos = TrackingPosition("s3_pos", s3, True)
        theta_ang = AngleParameter("Theta", theta, True)
        detector_position = TrackingPosition("det_pos", detector, True)
        detector_angle = AngleParameter("det_angle", detector, True)

        params = [slit1_pos, theta_ang, slit3_pos, detector_position, detector_angle]

        # DRIVES
        s1_axis = create_mock_axis("MOT:MTR0101", 0, 1)
        s3_axis = create_mock_axis("MOT:MTR0102", 0, 1)
        det_axis = create_mock_axis("MOT:MTR0104", 0, 1)
        det_angle_axis = create_mock_axis("MOT:MTR0105", 0, 1)
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

        slit1_pos.sp = 0
        slit3_pos.sp = 0
        detector_position.sp = 0
        detector_angle.sp = 0

        theta_angle = 2
        theta_ang.sp = theta_angle
        bl.move = 1

        assert_that(s1_axis.value, is_(0))

        expected_s3_value = SPACING * tan(radians(theta_angle * 2.0))
        assert_that(s3_axis.value, is_(expected_s3_value))

        expected_det_value = 2 * SPACING * tan(radians(theta_angle * 2.0))
        assert_that(det_axis.value, is_(expected_det_value))

        assert_that(det_angle_axis.value, is_(2*theta_angle))


if __name__ == '__main__':
    unittest.main()
