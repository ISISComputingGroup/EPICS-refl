import unittest

from math import tan, radians, isnan
from hamcrest import *
from mock import Mock, patch, call
from parameterized import parameterized

from ReflectometryServer.beam_path_calc import BeamPathUpdate, BeamPathCalcAxis
from ReflectometryServer.components import Component, ReflectingComponent, TiltingComponent, ThetaComponent
from ReflectometryServer.geometry import Position, PositionAndAngle, ChangeAxis
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.test_modules.utils import position_and_angle, position, DEFAULT_TEST_TOLERANCE


class TestBeamCalcPath(unittest.TestCase):

    def test_GIVEN_no_get_displacement_set_WHEN_get_displacement_THEN_Error(self):

        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(calling(calc_axis.get_displacement),
                    raises(TypeError, pattern="Axis does not support get_displacement"))

    def test_GIVEN_no_set_displacement_set_WHEN_set_displacement_THEN_Error(self):

        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(calling(calc_axis.set_displacement).with_args(None),
                    raises(TypeError, pattern="Axis does not support set_displacement"))

    def test_GIVEN_no_get_displacement_for_set_WHEN_call_define_event_THEN_Error(self):

        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(calling(calc_axis.define_axis_position_as).with_args(None),
                    raises(TypeError, pattern="Axis can not have its position defined"))

    def test_GIVEN_can_define_as_position_as_is_false_WHEN_call_define_event_THEN_Error(self):

        calc_axis = BeamPathCalcAxis(None, None, None, get_displacement_for=lambda x: x)
        calc_axis.can_define_axis_position_as = False

        assert_that(calling(calc_axis.define_axis_position_as).with_args(None),
                    raises(TypeError, pattern="Axis can not have its position defined"))

    def test_GIVEN_no_init_displacement_from_motor_WHEN_called_THEN_Error(self):

        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(calling(calc_axis.init_displacement_from_motor).with_args(None),
                    raises(TypeError, pattern="Axis does not support init_displacement_from_motor"))


if __name__ == '__main__':
    unittest.main()
