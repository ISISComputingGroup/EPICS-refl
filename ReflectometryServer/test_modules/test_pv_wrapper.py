import time

from hamcrest import *
from mock import Mock, patch
from parameterized import parameterized

import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer.ChannelAccess.constants import MOTOR_MOVING_PV
from ReflectometryServer.pv_wrapper import DEFAULT_SCALE_FACTOR, ProcessMonitorEvents
from ReflectometryServer.test_modules.data_mother import MockChannelAccess
from server_common.channel_access import UnableToConnectToPVException

FLOAT_TOLERANCE = 1e-9

TEST_PREFIX = "TEST:"


def _create_pv(pv, suffix):
    return "{}{}{}".format(TEST_PREFIX, pv, suffix)


class TestMotorPVWrapper(unittest.TestCase):

    def setUp(self):
        self.motor_name = "MOTOR"
        ReflectometryServer.pv_wrapper.MYPVPREFIX = TEST_PREFIX
        self.sp_pv = _create_pv(self.motor_name, "")
        self.rbv_pv = _create_pv(self.motor_name, ".RBV")
        self.mres_pv = _create_pv(self.motor_name, ".MRES")
        self.vmax_pv = _create_pv(self.motor_name, ".VMAX")
        self.vbas_pv = _create_pv(self.motor_name, ".VBAS")
        self.velo_pv = _create_pv(self.motor_name, ".VELO")
        self.bdst_pv = _create_pv(self.motor_name, ".BDST")
        self.bvel_pv = _create_pv(self.motor_name, ".BVEL")
        self.dir_pv = _create_pv(self.motor_name, ".DIR")
        self.dmov_pv = _create_pv(self.motor_name, ".DMOV")
        self.hlm_pv = _create_pv(self.motor_name, ".HLM")
        self.llm_pv = _create_pv(self.motor_name, ".LLM")
        self.sp = 1.0
        self.rbv = 1.1
        self.mres = 0.1
        self.vmax = 1
        self.vbas = 0.0
        self.velo = 0.5
        self.bdst = 0.05
        self.bvel = 0.1
        self.dir = "Pos"
        self.dmov = 1
        self.hlm = 10
        self.llm = -10
        self.mock_motor_pvs = {self.sp_pv: self.sp,
                               self.rbv_pv: self.rbv,
                               self.mres_pv: self.mres,
                               self.vmax_pv: self.vmax,
                               self.vbas_pv: self.vbas,
                               self.velo_pv: self.velo,
                               self.bdst_pv: self.bdst,
                               self.bvel_pv: self.bvel,
                               self.dir_pv: self.dir,
                               self.dmov_pv: self.dmov,
                               self.hlm_pv: self.hlm,
                               self.llm_pv: self.llm
                               }
        self.mock_ca = MockChannelAccess(self.mock_motor_pvs)
        self.wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_resolution_is_initialised_correctly(self):
        expected_resolution = self.mres

        self.wrapper.initialise()
        actual_resolution = self.wrapper.resolution

        self.assertEqual(expected_resolution, actual_resolution)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_velocity_is_initialised_correctly(self):
        expected_velocity = self.velo

        self.wrapper.initialise()
        actual_velocity = self.wrapper.velocity

        self.assertEqual(expected_velocity, actual_velocity)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_cached_velocity_is_restored(self):
        expected_velocity = self.velo

        self.wrapper.initialise()
        self.assertEqual(self.wrapper.is_moving, False)

        self.wrapper.cache_velocity()

        self.velo = self.vmax
        self.wrapper.velocity = self.vmax
        set_velocity = self.wrapper.velocity
        self.assertEqual(set_velocity, expected_velocity)

        self.wrapper.restore_pre_move_velocity()

        self.velo = self.wrapper.velocity

        self.assertEqual(expected_velocity, self.velo)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_max_velocity_is_initialised_correctly(self):
        expected_max_velocity = self.vmax

        self.wrapper.initialise()
        actual_max_velocity = self.wrapper.max_velocity

        self.assertEqual(expected_max_velocity, actual_max_velocity)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_setpoint_is_initialised_correctly(self):
        expected_sp = self.sp

        actual_sp = self.wrapper.sp

        self.assertEqual(expected_sp, actual_sp)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_readback_is_initialised_correctly(self):
        expected_rbv = self.rbv

        actual_rbv = self.wrapper.rbv

        self.assertEqual(expected_rbv, actual_rbv)

    def test_GIVEN_base_pv_and_positive_dir_WHEN_creating_motor_pv_wrapper_THEN_backlash_distance_is_initialised_correctly(self):
        self.mock_ca.caput(self.dir_pv, "Pos")
        expected_bdst = self.bdst * -1

        self.wrapper.initialise()
        actual_bdst = self.wrapper.backlash_distance

        self.assertEqual(expected_bdst, actual_bdst)

    def test_GIVEN_base_pv_and_negative_dir_WHEN_creating_motor_pv_wrapper_THEN_backlash_distance_is_initialised_correctly(self):
        self.mock_ca.caput(self.dir_pv, "Neg")
        expected_bdst = self.bdst

        self.wrapper.initialise()
        actual_bdst = self.wrapper.backlash_distance

        self.assertEqual(expected_bdst, actual_bdst)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_backlash_velocity_is_initialised_correctly(self):
        expected_bvel = self.bvel

        self.wrapper.initialise()
        actual_bvel = self.wrapper.backlash_velocity

        self.assertEqual(expected_bvel, actual_bvel)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_high_soft_limit_is_initialised_correctly(self):
        expected_hlm = self.hlm

        self.wrapper.initialise()
        actual_hlm = self.wrapper.hlm

        self.assertEqual(expected_hlm, actual_hlm)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_low_soft_limit_is_initialised_correctly(self):
        expected_llm = self.llm

        self.wrapper.initialise()
        actual_llm = self.wrapper.llm

        self.assertEqual(expected_llm, actual_llm)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_direction_is_initialised_correctly(self):
        expected_dir = self.dir

        self.wrapper.initialise()
        actual_dir = self.wrapper.direction

        self.assertEqual(expected_dir, actual_dir)

    def test_GIVEN_base_velocity_is_non_zero_WHEN_initialising_motor_pv_wrapper_THEN_min_velocity_set_to_vbas(self):
        vbas = 0.125
        self.mock_ca.caput(self.vbas_pv, vbas)
        expected_min_velocity = vbas

        self.wrapper.initialise()
        actual_min_velocity = self.wrapper.min_velocity

        assert_that(expected_min_velocity, is_(close_to(actual_min_velocity, FLOAT_TOLERANCE)))

    @parameterized.expand([(1,), (8,), (50,), (1000,)])
    def test_GIVEN_base_velocity_is_zero_and_scale_factor_is_custom_WHEN_initialising_motor_pv_wrapper_THEN_min_velocity_set_to_custom_fraction_of_vmax(self, scale_factor):
        expected_min_velocity = self.vmax / scale_factor
        self.wrapper_with_custom_scale_level = MotorPVWrapper(self.motor_name, ca=self.mock_ca, min_velocity_scale_factor=scale_factor)

        self.wrapper_with_custom_scale_level.initialise()
        actual_min_velocity = self.wrapper_with_custom_scale_level.min_velocity

        assert_that(expected_min_velocity, is_(close_to(actual_min_velocity, FLOAT_TOLERANCE)))

    def test_GIVEN_base_velocity_is_zero_and_scale_factor_is_nonsensical_WHEN_initialising_motor_pv_wrapper_THEN_min_velocity_set_to_default_fraction_of_vmax(self):
        scale_level = -4
        expected_scale_factor = 1.0 / DEFAULT_SCALE_FACTOR
        expected_min_velocity = self.vmax * expected_scale_factor
        self.wrapper_with_custom_scale_level = MotorPVWrapper(self.motor_name, ca=self.mock_ca, min_velocity_scale_factor=scale_level)

        self.wrapper_with_custom_scale_level.initialise()
        actual_min_velocity = self.wrapper_with_custom_scale_level.min_velocity

        assert_that(expected_min_velocity, is_(close_to(actual_min_velocity, FLOAT_TOLERANCE)))

    def test_GIVEN_base_velocity_is_zero_and_scale_factor_is_default_WHEN_initialising_motor_pv_wrapper_THEN_min_velocity_set_to_default_fraction_of_vmax(self):
        expected_min_velocity = self.vmax / DEFAULT_SCALE_FACTOR

        self.wrapper.initialise()
        actual_min_velocity = self.wrapper.min_velocity

        assert_that(expected_min_velocity, is_(close_to(actual_min_velocity, FLOAT_TOLERANCE)))

    def test_GIVEN_base_velocity_is_zero_and_scale_factor_is_zero_WHEN_initialising_motor_pv_wrapper_THEN_min_velocity_set_to_default(self):
        expected_min_velocity = self.vmax / DEFAULT_SCALE_FACTOR
        scale_factor = 0
        self.wrapper_with_custom_scale_level = MotorPVWrapper(self.motor_name, ca=self.mock_ca, min_velocity_scale_factor=scale_factor)

        self.wrapper_with_custom_scale_level.initialise()
        actual_min_velocity = self.wrapper_with_custom_scale_level.min_velocity

        assert_that(expected_min_velocity, is_(close_to(actual_min_velocity, FLOAT_TOLERANCE)))


class TestJawsAxisPVWrapper(unittest.TestCase):

    def setUp(self):
        ReflectometryServer.pv_wrapper.MYPVPREFIX = TEST_PREFIX
        self.jaws_name = "JAWS"
        self.vgap_sp_pv = _create_pv(self.jaws_name, ":VGAP:SP")
        self.vgap_rbv_pv = _create_pv(self.jaws_name, ":VGAP")
        self.vgap_dmov_pv = _create_pv(self.jaws_name, ":VGAP:DMOV")
        self.vcent_sp_pv = _create_pv(self.jaws_name, ":VCENT:SP")
        self.vcent_rbv_pv = _create_pv(self.jaws_name, ":VCENT")
        self.vcent_dmov_pv = _create_pv(self.jaws_name, ":VCENT:DMOV")
        self.hgap_sp_pv = _create_pv(self.jaws_name, ":HGAP:SP")
        self.hgap_rbv_pv = _create_pv(self.jaws_name, ":HGAP")
        self.hgap_dmov_pv = _create_pv(self.jaws_name, ":HGAP:DMOV")
        self.hcent_sp_pv = _create_pv(self.jaws_name, ":HCENT:SP")
        self.hcent_rbv_pv = _create_pv(self.jaws_name, ":HCENT")
        self.hcent_dmov_pv = _create_pv(self.jaws_name, ":HCENT:DMOV")
        self.vgap_sp = 1.0
        self.vgap_rbv = 1.1
        self.vcent_sp = 2.0
        self.vcent_rbv = 2.1
        self.hgap_sp = 3.0
        self.hgap_rbv = 3.1
        self.hcent_sp = 4.0
        self.hcent_rbv = 4.1
        self.dmov = 1
        self.mres = 0.1
        self.vmax = 1
        self.vbas = 0.0
        self.velo = 0.5
        self.mock_axis_pvs = {self.vgap_sp_pv: self.vgap_sp,
                              self.vgap_rbv_pv: self.vgap_rbv,
                              self.vgap_dmov_pv: self.dmov,
                              self.vcent_sp_pv: self.vcent_sp,
                              self.vcent_rbv_pv: self.vcent_rbv,
                              self.vcent_dmov_pv: self.dmov,
                              self.hgap_sp_pv: self.hgap_sp,
                              self.hgap_rbv_pv: self.hgap_rbv,
                              self.hgap_dmov_pv: self.dmov,
                              self.hcent_sp_pv: self.hcent_sp,
                              self.hcent_rbv_pv: self.hcent_rbv,
                              self.hcent_dmov_pv: self.dmov}
        for direction in ["JN", "JE", "JS", "JW"]:
            direction_pv = "{}:{}".format(self.jaws_name, direction)
            mres_pv = _create_pv(direction_pv, ":MTR.MRES")
            vmax_pv = _create_pv(direction_pv, ":MTR.VMAX")
            vbas_pv = _create_pv(direction_pv, ":MTR.VBAS")
            velo_pv = _create_pv(direction_pv, ":MTR.VELO")
            self.mock_axis_pvs[mres_pv] = self.mres
            self.mock_axis_pvs[vmax_pv] = self.vmax
            self.mock_axis_pvs[vbas_pv] = self.vbas
            self.mock_axis_pvs[velo_pv] = self.velo
        self.mock_ca = MockChannelAccess(self.mock_axis_pvs)

    def test_GIVEN_base_pv_and_motor_is_vertical_WHEN_creating_jawgap_wrapper_THEN_pvs_are_correct(self):
        expected_sp = self.vgap_sp
        expected_rbv = self.vgap_rbv

        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=True, ca=self.mock_ca)
        actual_sp = wrapper.sp
        actual_rbv = wrapper.rbv

        self.assertEqual(expected_sp, actual_sp)
        self.assertEqual(expected_rbv, actual_rbv)

    def test_GIVEN_base_pv_and_motor_is_horizontal_WHEN_creating_jawgap_wrapper_THEN_pvs_are_correct(self):
        expected_sp = self.hgap_sp
        expected_rbv = self.hgap_rbv

        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        actual_sp = wrapper.sp
        actual_rbv = wrapper.rbv

        self.assertEqual(expected_sp, actual_sp)
        self.assertEqual(expected_rbv, actual_rbv)

    def test_GIVEN_base_pv_and_motor_is_vertical_WHEN_creating_jawcent_wrapper_THEN_pvs_are_correct(self):
        expected_sp = self.vcent_sp
        expected_rbv = self.vcent_rbv

        wrapper = JawsCentrePVWrapper(self.jaws_name, is_vertical=True, ca=self.mock_ca)
        actual_sp = wrapper.sp
        actual_rbv = wrapper.rbv

        self.assertEqual(expected_sp, actual_sp)
        self.assertEqual(expected_rbv, actual_rbv)

    def test_GIVEN_base_pv_and_motor_is_horizontal_WHEN_creating_jawcent_wrapper_THEN_pvs_are_correct(self):
        expected_sp = self.hcent_sp
        expected_rbv = self.hcent_rbv

        wrapper = JawsCentrePVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        actual_sp = wrapper.sp
        actual_rbv = wrapper.rbv

        self.assertEqual(expected_sp, actual_sp)
        self.assertEqual(expected_rbv, actual_rbv)

    def test_GIVEN_initialised_jaw_gap_WHEN_get_backlash_distance_THEN_distance_is_0_because_jaws_do_not_backlash(self):
        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        wrapper.initialise()

        result = wrapper.backlash_distance

        assert_that(result, is_(0), "Jaws should not have backlash distance")

    def test_GIVEN_vbas_not_set_and_jaw_gap_initialised_WHEN_get_minimum_velocity_THEN_minimum_velocity_is_default(self):
        expected = self.vmax / DEFAULT_SCALE_FACTOR
        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        wrapper.initialise()

        result = wrapper.min_velocity

        assert_that(result, is_(expected))

    def test_GIVEN_soft_limits_not_set_and_jaw_gap_initialised_WHEN_get_limits_THEN_limits_are_infinity(self):
        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        wrapper.initialise()

        assert_that(wrapper.llm, is_(float('-inf')))
        assert_that(wrapper.hlm, is_(float('inf')))

    def test_GIVEN_soft_limits_not_set_and_jaw_centre_initialised_WHEN_get_limits_THEN_limits_are_infinity(self):
        wrapper = JawsCentrePVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        wrapper.initialise()

        assert_that(wrapper.llm, is_(float('-inf')))
        assert_that(wrapper.hlm, is_(float('inf')))

    def test_GIVEN_vbas_set_and_jaw_gap_initialised_WHEN_get_minimum_velocity_THEN_minimum_velocity_is_default(self):
        expected = 0.123
        for direction in ["JN", "JE", "JS", "JW"]:
            direction_pv = "{}:{}".format(self.jaws_name, direction)
            vbas_pv = _create_pv(direction_pv, ":MTR.VBAS")
            self.mock_axis_pvs[vbas_pv] = expected
        wrapper = JawsGapPVWrapper(self.jaws_name, is_vertical=False, ca=self.mock_ca)
        wrapper.initialise()

        result = wrapper.min_velocity

        assert_that(result, is_(expected))


class TestAggregateMonitorEvents(unittest.TestCase):

    def setUp(self):
        self.pme = ProcessMonitorEvents()
        self.event_arg = []

    def event(self, value):
        self.event_arg.append(value)

    def test_GIVEN_one_event_WHEN_processed_THEN_event_triggered(self):
        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_current_triggers()

        assert_that(self.event_arg, is_([expected_value]))

    def test_GIVEN_two_events_of_same_type_WHEN_processed_THEN_only_last_event_triggered(self):
        expected_value = "HI"
        self.pme.add_trigger(self.event, "not this one", start_processing=False)
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_current_triggers()

        assert_that(self.event_arg, is_([expected_value]))

    def test_GIVEN_two_events_of_different_type_WHEN_processed_THEN_both_events_triggered(self):
        expected_value1 = "HI"
        expected_value2 = 1
        self.pme.add_trigger(self.event, expected_value1, start_processing=False)
        self.pme.add_trigger(self.event, expected_value2, start_processing=False)

        self.pme.process_current_triggers()

        assert_that(self.event_arg, contains_inanyorder(expected_value1, expected_value2))

    def test_GIVEN_two_events_of_different_type_WHEN_processed_one_has_exception_THEN_only_non_exception_events_triggered(self):
        expected_value1 = "HI"
        expected_value2 = 1
        mock = Mock(side_effect=ValueError)
        self.pme.add_trigger(self.event, expected_value1, start_processing=False)
        self.pme.add_trigger(mock, "There", start_processing=False)
        self.pme.add_trigger(self.event, expected_value2, start_processing=False)

        self.pme.process_current_triggers()

        assert_that(self.event_arg, contains_inanyorder(expected_value1, expected_value2))

    def test_GIVEN_one_event_WHEN_processed_THEN_loop_is_terminated(self):
        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_triggers_loop()

        assert_that(self.event_arg, is_([expected_value]))

    def test_GIVEN_one_event_WHEN_added_THEN_event_is_processed(self):
        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_triggers_loop()

        assert_that(self.event_arg, is_([expected_value]))

    def test_GIVEN_nothing_WHEN_one_event_wait_then_second_event_THEN_events_are_both_processed(self):
        # check that the thread can be restarted

        for expected_value in ["HI", "THERE", "WORKS"]:
            self.pme.add_trigger(self.event, expected_value, start_processing=False)

            self.pme.process_triggers_loop()

            assert_that(self.event_arg, is_([expected_value]))
            self.event_arg = []

    @patch('ReflectometryServer.pv_wrapper.ChannelAccess')
    def test_GIVEN_nothing_WHEN_event_THEN_in_motion_flag_is_set(self, channel_access):
        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_triggers_loop()

        channel_access.caput.assert_any_call(MOTOR_MOVING_PV, 1, safe_not_quick=False)

    @patch('ReflectometryServer.pv_wrapper.ChannelAccess')
    def test_GIVEN_nothing_WHEN_no_more_events_THEN_in_motion_flag_is_cleared(self, channel_access):

        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_triggers_loop()
        channel_access.caput.assert_called_with(MOTOR_MOVING_PV, 0, safe_not_quick=False)

    @patch('ReflectometryServer.pv_wrapper.ChannelAccess')
    def test_GIVEN_moving_pv_does_not_exist_WHEN_event_THEN_event_is_processed(self, channel_access):
        channel_access.caput.side_effect = UnableToConnectToPVException("pvname", "error")
        expected_value = "HI"
        self.pme.add_trigger(self.event, expected_value, start_processing=False)

        self.pme.process_triggers_loop()
        assert_that(self.event_arg, is_([expected_value]))
