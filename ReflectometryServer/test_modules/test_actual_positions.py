import unittest

from hamcrest import *

from ReflectometryServer.components import ReflectingComponent, Component
from ReflectometryServer.geometry import PositionAndAngle, PositionAndAngle
from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.parameters import AngleParameter


class TestComponentBeamline(unittest.TestCase):

    def setUp(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=2.5)
        s0 = Component("s0", setup=PositionAndAngle(0, 0, 90))
        s1 = Component("s1", setup=PositionAndAngle(0, 1, 90))
        frame_overlap_mirror = ReflectingComponent("FOM", setup=PositionAndAngle(0, 2, 90))
        frame_overlap_mirror.beam_path_set_point.is_in_beam = False
        self.polarising_mirror = ReflectingComponent("Polariser", setup=PositionAndAngle(0, 3, 90))
        self.polarising_mirror.beam_path_set_point.is_in_beam = False
        s2 = Component("s2", setup=PositionAndAngle(0, 4, 90))
        self.ideal_sample_point = ReflectingComponent("ideal sample point", setup=PositionAndAngle(0, 5, 90))
        s3 = Component("s3", setup=PositionAndAngle(0, 6, 90))
        analyser = ReflectingComponent("analyser", setup=PositionAndAngle(0, 7, 90))
        analyser.beam_path_set_point.is_in_beam = False
        s4 = Component("s4", setup=PositionAndAngle(0, 8, 90))
        detector = Component("detector", setup=PositionAndAngle(0, 10, 90))

        theta = AngleParameter("theta", self.ideal_sample_point, sim=True)
        theta.sp_no_move = 0
        smangle = AngleParameter("smangle", self.polarising_mirror, sim=True)
        smangle.sp_no_move = 0

        self.nr_mode = BeamlineMode("NR Mode", [theta.name])
        self.polarised_mode = BeamlineMode("Polarised Mode", [smangle.name, theta.name])

        self.beamline = Beamline(
            [s0, s1, frame_overlap_mirror, self.polarising_mirror, s2, self.ideal_sample_point, s3, analyser, s4, detector],
            [smangle, theta],
            [],
            [self.nr_mode, self.polarised_mode],
            beam_start
        )

    def test_GIVEN_beam_line_contains_multiple_component_WHEN_set_theta_THEN_angle_between_incoming_and_outgoing_beam_is_correct(self):
        self.beamline.active_mode = self.nr_mode.name

        theta_set = 10.0
        self.beamline.parameter("theta").sp = theta_set

        reflection_angle = self.ideal_sample_point.beam_path_set_point.get_outgoing_beam().angle - self.ideal_sample_point.beam_path_set_point._incoming_beam.angle
        assert_that(reflection_angle, is_(theta_set * 2.0))

    def test_GIVEN_beam_line_contains_active_super_mirror_WHEN_set_theta_THEN_angle_between_incoming_and_outgoing_beam_is_correct(self):
        self.beamline.active_mode = self.polarised_mode.name
        theta_set = 10.0
        self.polarising_mirror.beam_path_set_point.is_in_beam = True
        self.beamline.parameter("smangle").sp = 10

        self.beamline.parameter("theta").sp = theta_set

        reflection_angle = self.ideal_sample_point.beam_path_set_point.get_outgoing_beam().angle - self.ideal_sample_point.beam_path_set_point._incoming_beam.angle
        assert_that(reflection_angle, is_(theta_set * 2.0))

    def test_GIVEN_beam_line_contains_active_super_mirror_WHEN_angle_set_THEN_angle_between_incoming_and_outgoing_beam_is_correct(self):
        self.beamline.active_mode = self.polarised_mode.name
        theta_set = 10.0
        self.beamline.parameter("theta").sp = theta_set
        self.polarising_mirror.beam_path_set_point.is_in_beam = True

        self.beamline.parameter("smangle").sp = 10

        reflection_angle = self.ideal_sample_point.beam_path_set_point.get_outgoing_beam().angle - self.ideal_sample_point.beam_path_set_point._incoming_beam.angle
        assert_that(reflection_angle, is_(theta_set * 2.0))


if __name__ == '__main__':
    unittest.main()
