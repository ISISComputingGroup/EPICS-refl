import unittest

from math import tan, radians
from hamcrest import *
from mock import Mock

from ReflectometryServer.components import ReflectingComponent, Component
from ReflectometryServer.movement_strategy import LinearMovement
from ReflectometryServer.geometry import PositionAndAngle
from ReflectometryServer.beamline import Beamline
from ReflectometryServer.test_modules.data_mother import DataMother
from utils import position_and_angle


class TestComponentBeamline(unittest.TestCase):

    def setup_beamline(self, initial_mirror_angle, mirror_position, beam_start):
        jaws = Component("jaws", movement_strategy=LinearMovement(0, 0, 90))
        mirror = ReflectingComponent("mirror", movement_strategy=LinearMovement(0, mirror_position, 90))
        mirror.beam_path_set_point.angle = initial_mirror_angle
        jaws3 = Component("jaws3", movement_strategy=LinearMovement(0, 20, 90))
        beamline = Beamline([jaws, mirror, jaws3], [], [], [], beam_start)
        return beamline, mirror

    def test_GIVEN_beam_line_contains_one_passive_component_WHEN_beam_set_THEN_component_has_beam_out_same_as_beam_in(self):
        beam_start = PositionAndAngle(y=0, z=0, angle=0)
        jaws = Component("jaws", movement_strategy=LinearMovement(0, 2, 90))
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
        comp1 = Component("comp1", LinearMovement(0, 1, 90))
        comp2 = Component("comp2", LinearMovement(0, 2, 90))
        beamline = Beamline([comp1, comp2], [], [], [DataMother.BEAMLINE_MODE_EMPTY])

        callback = Mock()
        comp2.beam_path_rbv.set_incoming_beam = callback
        comp1.beam_path_rbv.set_displacement(1.0)

        assert_that(callback.called, is_(True))


if __name__ == '__main__':
    unittest.main()
