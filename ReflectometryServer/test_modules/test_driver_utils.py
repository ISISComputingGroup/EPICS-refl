import unittest

from hamcrest import *
from server_common.channel_access import AlarmSeverity, AlarmStatus

from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.ChannelAccess.driver_utils import DriverParamHelper
from ReflectometryServer.ChannelAccess.pv_manager import PVManager
from ReflectometryServer.parameters import EnumParameter, ParameterUpdateBase


class TestDriverUtils(unittest.TestCase):

    def setUp(self) -> None:
        self.param_name = "ENUM"
        self.pvname = "PARAM:{}".format(self.param_name)
        self.opt1 = "opt1"
        options = [self.opt1, "opt2"]
        self.index_of_opt1 = 0
        self.param = EnumParameter(self.param_name, options)
        bl = Beamline([], [self.param], [], [BeamlineMode("mode", [])])

        pvmanager = PVManager()
        pvmanager.set_beamline(bl)

        self.driver_helper = DriverParamHelper(pvmanager, bl)

    def test_GIVEN_enum_param_WHEN_set_from_pv_THEN_parameter_is_set(self):

        self.driver_helper.param_write("{}:SP".format(self.pvname), self.index_of_opt1)

        assert_that(self.param.sp, is_(self.opt1))

    def test_GIVEN_enum_param_WHEN_get_monitor_updates_THEN_all_pvs_and_values_returned(self):

        result = list(self.driver_helper.get_param_monitor_updates())

        pvname = self.pvname
        index_of_opt1 = self.index_of_opt1
        assert_that(result, contains_inanyorder(("{}".format(pvname), index_of_opt1, None, None),
                                                ("{}:SP".format(pvname), index_of_opt1, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:SP:RBV".format(pvname), index_of_opt1, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:SP_NO_ACTION".format(pvname), index_of_opt1, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:CHANGED".format(pvname), False, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:ACTION".format(pvname), 0, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:RBV:AT_SP".format(pvname), True, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:LOCKED".format(pvname), False, AlarmSeverity.No, AlarmSeverity.No),
                                                ("{}:READ_ONLY".format(pvname), False, AlarmSeverity.No, AlarmSeverity.No),
                                                ))

    def test_GIVEN_enum_param_WHEN_update_event_processed_using_get_param_update_from_event_THEN_fields_(self):
        expected_severity = AlarmSeverity.Major
        expected_status = AlarmStatus.HiHi
        update = ParameterUpdateBase(self.opt1, expected_severity, expected_status)

        result_name, result_value, result_severity, result_status = \
            self.driver_helper.get_param_update_from_event(self.pvname, self.param.parameter_type, update)

        assert_that(result_name, is_(self.pvname))
        assert_that(result_value, is_(self.index_of_opt1))
        assert_that(result_severity, is_(expected_severity))
        assert_that(result_status, is_(expected_status))

    def test_GIVEN_enum_param_WHEN_update_event_processed_using_get_param_update_from_event_with_to_large_status_indexTHEN_index_capped_at_15(self):
        expected_severity = AlarmSeverity.Major
        expected_status = 32
        update = ParameterUpdateBase(self.opt1, expected_severity, expected_status)

        result_name, result_value, result_severity, result_status = \
            self.driver_helper.get_param_update_from_event(self.pvname, self.param.parameter_type, update)

        assert_that(result_name, is_(self.pvname))
        assert_that(result_value, is_(self.index_of_opt1))
        assert_that(result_severity, is_(expected_severity))
        assert_that(int(result_status), is_(15))

    def test_GIVEN_enum_param_WHEN_update_event_processed_using_get_param_update_from_event_and_value_is_not_in_enum_THEN_value_is_set_to_minus_one_and_error_in_alarms(self):
        expected_severity = AlarmSeverity.Invalid
        expected_status = AlarmStatus.State
        update = ParameterUpdateBase("not an option", expected_severity, expected_status)

        result_name, result_value, result_severity, result_status = \
            self.driver_helper.get_param_update_from_event(self.pvname, self.param.parameter_type, update)

        assert_that(result_name, is_(self.pvname))
        assert_that(result_value, is_(-1))
        assert_that(result_severity, is_(expected_severity))
        assert_that(result_status, is_(expected_status))

    def test_GIVEN_enum_param_WHEN_update_event_processed_using_get_param_update_from_event_and_value_is_None_THEN_value_is_set_to_minus_one_and_error_in_alarms(self):
        expected_severity = AlarmSeverity.Invalid
        expected_status = AlarmStatus.State
        update = ParameterUpdateBase(None, expected_severity, expected_status)

        result_name, result_value, result_severity, result_status = \
            self.driver_helper.get_param_update_from_event(self.pvname, self.param.parameter_type, update)

        assert_that(result_name, is_(self.pvname))
        assert_that(result_value, is_(-1))
        assert_that(result_severity, is_(expected_severity))
        assert_that(result_status, is_(expected_status))

if __name__ == '__main__':
    unittest.main()
