import ReflectometryServer
import unittest

from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import MockChannelAccess

from server_common.channel_access import UnableToConnectToPVException

FLOAT_TOLERANCE = 1e-9

TEST_PREFIX = "TEST:"


class TestMotorPVWrapper(unittest.TestCase):

    def _create_pv(self, suffix):
        return "{}{}{}".format(TEST_PREFIX, self.motor_name, suffix)

    def setUp(self):
        self.motor_name = "MOTOR"
        ReflectometryServer.pv_wrapper.MYPVPREFIX = TEST_PREFIX
        self.sp_pv = self._create_pv("")
        self.rbv_pv = self._create_pv(".RBV")
        self.mres_pv = self._create_pv(".MRES")
        self.vmax_pv = self._create_pv(".VMAX")
        self.velo_pv = self._create_pv(".VELO")
        self.dmov_pv = self._create_pv(".DMOV")
        self.sp = 1.0
        self.rbv = 0.9
        self.mres = 0.1
        self.vmax = 1
        self.velo = 0.5
        self.mock_pvs = {self.sp_pv: self.sp,
                         self.rbv_pv: self.rbv,
                         self.mres_pv: self.mres,
                         self.vmax_pv: self.vmax,
                         self.velo_pv: self.velo
                         }
        self.mock_ca = MockChannelAccess(self.mock_pvs)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_resolution_is_initialised_correctly(self):
        expected_resolution = self.mres

        wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)
        actual_resolution = wrapper.resolution

        self.assertEqual(expected_resolution, actual_resolution)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_velocity_is_initialised_correctly(self):
        expected_velocity = self.velo

        wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)
        actual_velocity = wrapper.velocity

        self.assertEqual(expected_velocity, actual_velocity)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_max_velocity_is_initialised_correctly(self):
        expected_max_velocity = self.vmax

        wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)
        actual_max_velocity = wrapper.max_velocity

        self.assertEqual(expected_max_velocity, actual_max_velocity)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_setpoint_is_initialised_correctly(self):
        expected_sp = self.sp

        wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)
        actual_sp = wrapper.sp

        self.assertEqual(expected_sp, actual_sp)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_readback_is_initialised_correctly(self):
        expected_rbv = self.rbv

        wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)
        actual_rbv = wrapper.rbv

        self.assertEqual(expected_rbv, actual_rbv)
