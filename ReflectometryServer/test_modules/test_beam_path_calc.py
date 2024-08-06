import unittest

from hamcrest import *
from mock import MagicMock
from server_common.channel_access import AlarmSeverity, AlarmStatus

from ReflectometryServer.axis import BeamPathCalcAxis, ComponentAxis
from ReflectometryServer.beam_path_calc import (
    BeamPathCalcThetaRBV,
    BeamPathCalcThetaSP,
    TrackingBeamPathCalc,
)
from ReflectometryServer.components import Component
from ReflectometryServer.geometry import ChangeAxis, PositionAndAngle
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate


class TestBeamPathCalc(unittest.TestCase):
    def test_GIVEN_no_get_displacement_set_WHEN_get_displacement_THEN_Error(self):
        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(
            calling(calc_axis.get_displacement),
            raises(TypeError, pattern="Axis does not support get_displacement"),
        )

    def test_GIVEN_no_set_displacement_set_WHEN_set_displacement_THEN_Error(self):
        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(
            calling(calc_axis.set_displacement).with_args(
                CorrectedReadbackUpdate(None, None, None)
            ),
            raises(TypeError, pattern="Axis does not support set_displacement"),
        )

    def test_GIVEN_no_get_displacement_for_set_WHEN_call_define_event_THEN_Error(self):
        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(
            calling(calc_axis.define_axis_position_as).with_args(None),
            raises(TypeError, pattern="Axis can not have its position defined"),
        )

    def test_GIVEN_can_define_position_as_is_false_WHEN_call_define_event_THEN_Error(self):
        calc_axis = BeamPathCalcAxis(None, None, None, get_displacement_for=lambda x: x)
        calc_axis.can_define_axis_position_as = False

        assert_that(
            calling(calc_axis.define_axis_position_as).with_args(None),
            raises(TypeError, pattern="Axis can not have its position defined"),
        )

    def test_GIVEN_no_init_displacement_from_motor_WHEN_called_THEN_Error(self):
        calc_axis = BeamPathCalcAxis(None, None, None)

        assert_that(
            calling(calc_axis.init_displacement_from_motor).with_args(None),
            raises(TypeError, pattern="Axis does not support init_displacement_from_motor"),
        )

    def test_GIVEN_theta_sp_beam_path_calc_WHEN_add_CHI_axis_and_update_THEN_error(self):
        theta_sp = BeamPathCalcThetaSP("theta", None)
        comp = Component("comp", PositionAndAngle(0, 0, 0))
        theta_sp.add_angle_to(comp.beam_path_rbv, [ChangeAxis.CHI])

        assert_that(
            calling(comp.beam_path_rbv.axis[ChangeAxis.CHI].init_displacement_from_motor).with_args(
                10
            ),
            raises(RuntimeError),
        )

    def test_GIVEN_theta_rbv_beam_path_calc_WHEN_add_CHI_axis_and_set_displacement_THEN_error(self):
        theta_sp = BeamPathCalcThetaRBV("theta", None, None)
        comp = Component("comp", PositionAndAngle(0, 0, 0))
        theta_sp.add_angle_to(comp.beam_path_rbv, comp.beam_path_set_point, [ChangeAxis.CHI])

        assert_that(
            calling(comp.beam_path_rbv.axis[ChangeAxis.CHI].set_displacement).with_args(
                CorrectedReadbackUpdate(10, None, None)
            ),
            raises(RuntimeError),
        )


class TestBeamPathCalcThetaRBVAlarmCalc(unittest.TestCase):
    axes = [ChangeAxis.POSITION, ChangeAxis.LONG_AXIS]

    def set_up_alarms(self, first_alarm, second_alarm):
        position_axis = MagicMock(ComponentAxis)
        position_axis.alarm = first_alarm
        long_axis = MagicMock(ComponentAxis)
        long_axis.alarm = second_alarm
        rbv_beam_path_calc = MagicMock(TrackingBeamPathCalc)
        rbv_beam_path_calc.axis = {
            ChangeAxis.POSITION: position_axis,
            ChangeAxis.LONG_AXIS: long_axis,
        }
        return rbv_beam_path_calc

    def test_GIVEN_all_axis_ok_WHEN_alarm_calced_THEN_no_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.No, AlarmStatus.No), (AlarmSeverity.No, AlarmStatus.No)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.No)
        self.assertEqual(status, AlarmStatus.No)

    def test_GIVEN_one_axis_undefined_WHEN_alarm_calced_THEN_no_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.Invalid, AlarmStatus.UDF), (AlarmSeverity.No, AlarmStatus.No)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.No)
        self.assertEqual(status, AlarmStatus.No)

    def test_GIVEN_both_axes_undefined_WHEN_alarm_calced_THEN_undefined_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.Invalid, AlarmStatus.UDF), (AlarmSeverity.Invalid, AlarmStatus.UDF)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.Invalid)
        self.assertEqual(status, AlarmStatus.UDF)

    def test_GIVEN_one_axis_major_other_undefined_WHEN_alarm_calced_THEN_major_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.Invalid, AlarmStatus.UDF), (AlarmSeverity.Major, AlarmStatus.HiHi)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.Major)
        self.assertEqual(status, AlarmStatus.HiHi)

    def test_GIVEN_one_axis_major_other_no_alarm_WHEN_alarm_calced_THEN_major_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.No, AlarmStatus.No), (AlarmSeverity.Major, AlarmStatus.HiHi)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.Major)
        self.assertEqual(status, AlarmStatus.HiHi)

    def test_GIVEN_one_axis_major_other_minor_WHEN_alarm_calced_THEN_major_alarm(self):
        rbv_beam_path = self.set_up_alarms(
            (AlarmSeverity.Minor, AlarmStatus.High), (AlarmSeverity.Major, AlarmStatus.HiHi)
        )
        severity, status = BeamPathCalcThetaRBV.calculate_alarm_based_on_axes(
            self.axes, rbv_beam_path
        )
        self.assertEqual(severity, AlarmSeverity.Major)
        self.assertEqual(status, AlarmStatus.HiHi)


if __name__ == "__main__":
    unittest.main()
