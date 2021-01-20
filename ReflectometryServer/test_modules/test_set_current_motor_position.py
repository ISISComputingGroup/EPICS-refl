from math import tan

from mock import Mock
from parameterized import parameterized

import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer.axis import DefineValueAsEvent
from ReflectometryServer import ChangeAxis
from ReflectometryServer.parameters import RequestMoveEvent
from ReflectometryServer.pv_wrapper import JawsAxisPVWrapper
from ReflectometryServer.test_modules.data_mother import MockChannelAccess, create_mock_JawsCentrePVWrapper, \
    create_mock_axis
from ReflectometryServer.test_modules.utils import create_parameter_with_initial_value

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
        theta_component = ThetaComponent("comp", PositionAndAngle(0, 0, 90))
        component = Component("comp", PositionAndAngle(0, 1, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        theta_component.add_angle_to(component)
        parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        theta = AxisParameter("theta", theta_component, ChangeAxis.ANGLE)
        component.beam_path_rbv.axis[ChangeAxis.POSITION].add_listener(DefineValueAsEvent, _listener)

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
        parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        component.beam_path_rbv.axis[ChangeAxis.ANGLE].add_listener(DefineValueAsEvent, _listener)

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
        parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        component.beam_path_rbv.axis[ChangeAxis.ANGLE].add_listener(DefineValueAsEvent, _listener)

        parameter.define_current_value_as.new_value = position_to_set

        assert_that(self.set_position_to.new_position, is_(expected_position))
        assert_that(self.set_position_to.change_axis, is_(ChangeAxis.ANGLE))

    def test_GIVEN_angle_beamline_parameter_and_theta_component_WHEN_set_position_to_THEN_error(self):
        component = ThetaComponent("comp", PositionAndAngle(0, 0, 90))
        detector = Component("detector", PositionAndAngle(1, 0, 90))
        component.add_angle_to(detector)
        parameter = AxisParameter("param", component, ChangeAxis.ANGLE)

        assert_that(parameter.define_current_value_as, is_(None))

    def test_GIVEN_beamline_parameter_and_DirectParameter_component_WHEN_set_position_to_THEN_component_has_set_position_on(self):

        def _listener(set_position_to):
            self.set_position_to = set_position_to

        expected_position = 1
        mock_jaws_wrapper = create_mock_JawsCentrePVWrapper("jaws_centre", expected_position, 1)
        parameter = create_parameter_with_initial_value(0, DirectParameter, "param", mock_jaws_wrapper)
        mock_jaws_wrapper.sp = 0

        parameter.define_current_value_as.new_value = expected_position

        mock_jaws_wrapper.define_position_as.assert_called_once_with(expected_position)

    def test_GIVEN_InOutParameter_WHEN_get_set_position_to_THEN_it_is_none(self):

        parameter = InBeamParameter("param", Component("comp", PositionAndAngle(0, 0, 0)))

        assert_that(parameter.define_current_value_as, is_(None))

    def test_GIVEN_tracking_beamline_parameter_and_component_WHEN_set_position_to_THEN_component_and_parameter_set_points_are_new_values_motor_is_not_moved(self):
        incoming_beam = PositionAndAngle(0, 0, 0)
        expected_position = 1
        component = Component("comp", PositionAndAngle(0, 0, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        parameter = AxisParameter("param", component, ChangeAxis.POSITION)
        parameter.sp = 0
        parameter.move = 0
        move_listener = Mock()
        parameter.add_listener(RequestMoveEvent, move_listener)

        parameter.define_current_value_as.new_value = expected_position

        assert_that(component.beam_path_set_point.axis[ChangeAxis.POSITION].get_relative_to_beam(), is_(expected_position),
                    "component setpoint")
        assert_that(parameter.sp, is_(expected_position), "Parameter setpoint")
        assert_that(parameter.sp_rbv, is_(expected_position), "Parameter setpoint read back")
        move_listener.assert_not_called()

    def test_GIVEN_angle_beamline_parameter_and_component_WHEN_set_position_to_THEN_component_and_parameter_set_points_are_new_values(self):
        incoming_beam = PositionAndAngle(0, 0, 0)
        expected_position = 1
        component = TiltingComponent("comp", PositionAndAngle(0, 0, 90))
        component.beam_path_rbv.set_incoming_beam(incoming_beam)
        parameter = AxisParameter("param", component, ChangeAxis.ANGLE)
        parameter.sp = 0
        parameter.move = 0

        parameter.define_current_value_as.new_value = expected_position

        assert_that(component.beam_path_set_point.axis[ChangeAxis.ANGLE].get_relative_to_beam(), is_(expected_position),
                    "component setpoint")
        assert_that(parameter.sp, is_(expected_position), "Parameter setpoint")
        assert_that(parameter.sp_rbv, is_(expected_position), "Parameter setpoint read back")

    def test_GIVEN_beamline_parameter_and_DirectParameter_component_WHEN_set_position_to_THEN_setpoint_is_set_to_new_position(self):

        expected_position = 1
        expected_mock_jaws_wrapper_value = 10
        mock_jaws_wrapper = create_mock_JawsCentrePVWrapper("jaws_centre", expected_mock_jaws_wrapper_value, 1)

        parameter = create_parameter_with_initial_value(0, DirectParameter, "param", mock_jaws_wrapper)
        mock_jaws_wrapper.sp = 0
        parameter.sp = expected_mock_jaws_wrapper_value

        parameter.define_current_value_as.new_value = expected_position

        assert_that(parameter.sp, is_(expected_position))
        assert_that(parameter.sp_rbv, is_(expected_position))
        assert_that(mock_jaws_wrapper.last_set_point_set, is_(expected_mock_jaws_wrapper_value), "sp should not be set")


class TestCurrentMotorPositionEventsToMotor(unittest.TestCase):
    """
    Test for setting the current motor position
    """

    def test_GIVEN_displacement_driver_no_engineering_correction_WHEN_receive_set_position_as_event_for_positionset_THEN_motor_position_is_set(self):
        expected_position = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = IocDriver(component, ChangeAxis.POSITION, mock_axis)

        component.beam_path_rbv.axis[ChangeAxis.POSITION].trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.POSITION))

        assert_that(mock_axis.set_position_as_value, is_(expected_position))

    def test_GIVEN_displacement_driver_with_engineering_correction_WHEN_receive_set_position_as_event_for_positionset_THEN_motor_position_is_set_with_correction(self):
        expected_position = 1
        correction = 1

        component = Component("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = IocDriver(component, ChangeAxis.POSITION, mock_axis,
                           engineering_correction=ConstantCorrection(correction))

        component.beam_path_rbv.axis[ChangeAxis.POSITION].trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.POSITION))

        assert_that(mock_axis.set_position_as_value, is_(expected_position + correction))

    def test_GIVEN_displacement_driver_no_engineering_correction_WHEN_receive_set_angle_as_event_for_position_set_THEN_motor_position_is_not_set(self):
        expected_position = 1

        component = TiltingComponent("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = IocDriver(component, ChangeAxis.POSITION, mock_axis)

        component.beam_path_rbv.axis[ChangeAxis.ANGLE].trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.ANGLE))

        assert_that(mock_axis.set_position_as_value, is_(None))

    def test_GIVEN_angle_driver_no_engineering_correction_WHEN_receive_set_angle_as_event_for_positionset_THEN_motor_position_is_set(self):
        expected_position = 1

        component = TiltingComponent("comp", PositionAndAngle(0, 0, 0))
        mock_axis = create_mock_axis("axis", 0, 1)
        driver = IocDriver(component, ChangeAxis.ANGLE, mock_axis)

        component.beam_path_rbv.axis[ChangeAxis.ANGLE].trigger_listeners(DefineValueAsEvent(expected_position, ChangeAxis.ANGLE))

        assert_that(mock_axis.set_position_as_value, is_(expected_position))
