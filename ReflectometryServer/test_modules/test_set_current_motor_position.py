from math import tan

from mock import Mock
from parameterized import parameterized

import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer.components import DefineValueAsEvent, ChangeAxis
from ReflectometryServer.pv_wrapper import _JawsAxisPVWrapper
from ReflectometryServer.test_modules.data_mother import MockChannelAccess, create_mock_JawsCentrePVWrapper, \
    create_mock_axis

from server_common.channel_access import UnableToConnectToPVException
from hamcrest import *


class TestCurrentMotorPositionParametersToEven_inDriver(unittest.TestCase):
    """
    Test for setting the current motor position
    """
    def setUp(self):
        self.set_position_to = None

    @parameterized.expand([(0,),
                           (1,)])
    def test_GIVEN_tracking_beamline_parameter_and_component_WHEN_set_position_to_THEN_component_has_set_position_on(self, beam_path_height):
        incoming_beam = PositionAndAngle(beam_path_height, 0, 0)

        def _listener(set_position_to):
            self.set_position_to = set_position_to

        position_to_set = 1
        expected_position = position_to_set + beam_path_height
        component = Component("comp", PositionAndAngle(0, 0, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        parameter = TrackingPosition("param", component)
        component.add_listener(DefineValueAsEvent, _listener)

        parameter.define_current_value_as.new_value = position_to_set

        assert_that(self.set_position_to.new_position, is_(expected_position))
        assert_that(self.set_position_to.change_axis, is_(ChangeAxis.POSITION))

    @parameterized.expand([(0,),
                           (1,)])
    def test_GIVEN_angle_beamline_parameter_and_reflecting_component_WHEN_set_position_to_THEN_component_has_set_position_on(self, beam_path_angle):
        incoming_beam = PositionAndAngle(0, 0, beam_path_angle)

        def _listener(set_position_to):
            self.set_position_to = set_position_to

        position_to_set = 1
        expected_position = position_to_set + beam_path_angle
        component = ReflectingComponent("comp", PositionAndAngle(0, 0, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        parameter = AngleParameter("param", component)
        component.add_listener(DefineValueAsEvent, _listener)

        parameter.define_current_value_as.new_value = position_to_set

        assert_that(self.set_position_to.new_position, is_(expected_position))
        assert_that(self.set_position_to.change_axis, is_(ChangeAxis.ANGLE))

    @parameterized.expand([(0,),
                           (1,)])
    def test_GIVEN_angle_beamline_parameter_and_tilting_component_WHEN_set_position_to_THEN_component_has_set_position_on(self, beam_path_angle):
        incoming_beam = PositionAndAngle(0, 0, beam_path_angle)

        def _listener(set_position_to):
            self.set_position_to = set_position_to

        position_to_set = 1
        expected_position = position_to_set + beam_path_angle
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        parameter = AngleParameter("param", component)
        component.add_listener(DefineValueAsEvent, _listener)

        parameter.define_current_value_as.new_value = position_to_set

        assert_that(self.set_position_to.new_position, is_(expected_position))
        assert_that(self.set_position_to.change_axis, is_(ChangeAxis.ANGLE))

    def test_GIVEN_angle_beamline_parameter_and_theta_component_WHEN_set_position_to_THEN_error(self):

        detector = Component("detector", PositionAndAngle(1, 0, 90))
        component = ThetaComponent("comp", PositionAndAngle(0, 0, 90), angle_to=[detector])
        parameter = AngleParameter("param", component)

        assert_that(parameter.define_current_value_as, is_(None))

    def test_GIVEN_beamline_parameter_and_SlitGapParameter_component_WHEN_set_position_to_THEN_component_has_set_position_on(self):


        def _listener(set_position_to):
            self.set_position_to = set_position_to

        expected_position = 1
        mock_jaws_wrapper = create_mock_JawsCentrePVWrapper()
        parameter = SlitGapParameter("param", mock_jaws_wrapper)

        parameter.define_current_value_as.new_value = expected_position

        mock_jaws_wrapper.define_current_value_as.assert_called_once_with(expected_position)

    def test_GIVEN_InOutParameter_WHEN_get_set_position_to_THEN_it_is_none(self):

        parameter = InBeamParameter("param", Component("comp", PositionAndAngle(0, 0, 0)))

        assert_that(parameter.define_current_value_as, is_(None))


class TestCurrentMotorPositionEventsToMotor(unittest.TestCase):
    """
    Test for setting the current motor position
    """

    def test_GIVEN_displacement_driver_no_engineering_correction_WHEN_recieve_set_position_as_event_for_positionset_THEN_motor_position_is_set(self):
        expected_position = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = DisplacementDriver(component, mock_axis)

        component.trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.POSITION))

        assert_that(mock_axis.set_position_as_value, is_(expected_position))

    def test_GIVEN_displacement_driver_with_engineering_correction_WHEN_recieve_set_position_as_event_for_positionset_THEN_motor_position_is_set_with_correction(self):
        expected_position = 1
        correction = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = DisplacementDriver(component, mock_axis, engineering_correction=ConstantCorrection(correction))

        component.trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.POSITION))

        assert_that(mock_axis.set_position_as_value, is_(expected_position + correction))

    def test_GIVEN_displacement_driver_no_engineering_correction_WHEN_recieve_set_angle_as_event_for_position_set_THEN_motor_position_is_not_set(self):
        expected_position = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = DisplacementDriver(component, mock_axis)

        component.trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.ANGLE))

        assert_that(mock_axis.set_position_as_value, is_(None))

    def test_GIVEN_angle_driver_no_engineering_correction_WHEN_receive_set_angle_as_event_for_positionset_THEN_motor_position_is_set(self):
        expected_position = 1

        component = TiltingComponent("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = AngleDriver(component, mock_axis)

        component.trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.ANGLE))

        assert_that(mock_axis.set_position_as_value, is_(expected_position))
