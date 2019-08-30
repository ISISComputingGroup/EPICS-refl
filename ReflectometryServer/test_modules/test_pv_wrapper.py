import ReflectometryServer
import unittest

from ReflectometryServer import *
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
        self.velo_pv = _create_pv(self.motor_name, ".VELO")
        self.bdst_pv = _create_pv(self.motor_name, ".BDST")
        self.bvel_pv = _create_pv(self.motor_name, ".BVEL")
        self.dir_pv = _create_pv(self.motor_name, ".DIR")
        self.sp = 1.0
        self.rbv = 1.1
        self.mres = 0.1
        self.vmax = 1
        self.velo = 0.5
        self.bdst = 0.05
        self.bvel = 0.1
        self.dir = "Pos"
        self.mock_motor_pvs = {self.sp_pv: self.sp,
                               self.rbv_pv: self.rbv,
                               self.mres_pv: self.mres,
                               self.vmax_pv: self.vmax,
                               self.velo_pv: self.velo,
                               self.bdst_pv: self.bdst,
                               self.bvel_pv: self.bvel,
                               self.dir_pv: self.dir
                               }
        self.mock_ca = MockChannelAccess(self.mock_motor_pvs)
        self.wrapper = MotorPVWrapper(self.motor_name, ca=self.mock_ca)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_resolution_is_initialised_correctly(self):
        expected_resolution = self.mres

        actual_resolution = self.wrapper.resolution

        self.assertEqual(expected_resolution, actual_resolution)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_velocity_is_initialised_correctly(self):
        expected_velocity = self.velo

        self.wrapper.initialise()
        actual_velocity = self.wrapper.velocity

        self.assertEqual(expected_velocity, actual_velocity)

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_max_velocity_is_initialised_correctly(self):
        expected_max_velocity = self.vmax

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

    def test_GIVEN_base_pv_WHEN_creating_motor_pv_wrapper_THEN_direction_is_initialised_correctly(self):
        expected_dir = self.dir

        self.wrapper.initialise()
        actual_dir = self.wrapper.direction

        self.assertEqual(expected_dir, actual_dir)


class TestJawsAxisPVWrapper(unittest.TestCase):

    def setUp(self):
        ReflectometryServer.pv_wrapper.MYPVPREFIX = TEST_PREFIX
        self.jaws_name = "JAWS"
        self.vgap_sp_pv = _create_pv(self.jaws_name, ":VGAP:SP")
        self.vgap_rbv_pv = _create_pv(self.jaws_name, ":VGAP")
        self.vcent_sp_pv = _create_pv(self.jaws_name, ":VCENT:SP")
        self.vcent_rbv_pv = _create_pv(self.jaws_name, ":VCENT")
        self.hgap_sp_pv = _create_pv(self.jaws_name, ":HGAP:SP")
        self.hgap_rbv_pv = _create_pv(self.jaws_name, ":HGAP")
        self.hcent_sp_pv = _create_pv(self.jaws_name, ":HCENT:SP")
        self.hcent_rbv_pv = _create_pv(self.jaws_name, ":HCENT")
        self.vgap_sp = 1.0
        self.vgap_rbv = 1.1
        self.vcent_sp = 2.0
        self.vcent_rbv = 2.1
        self.hgap_sp = 3.0
        self.hgap_rbv = 3.1
        self.hcent_sp = 4.0
        self.hcent_rbv = 4.1
        self.mock_axis_pvs = {self.vgap_sp_pv: self.vgap_sp,
                              self.vgap_rbv_pv: self.vgap_rbv,
                              self.vcent_sp_pv: self.vcent_sp,
                              self.vcent_rbv_pv: self.vcent_rbv,
                              self.hgap_sp_pv: self.hgap_sp,
                              self.hgap_rbv_pv: self.hgap_rbv,
                              self.hcent_sp_pv: self.hcent_sp,
                              self.hcent_rbv_pv: self.hcent_rbv}
        for direction in ["JN", "JE", "JS", "JW"]:
            direction_pv = "{}:{}".format(self.jaws_name, direction)
            mres_pv = _create_pv(direction_pv, ":MTR.MRES")
            vmax_pv = _create_pv(direction_pv, ":MTR.VMAX")
            velo_pv = _create_pv(direction_pv, ":MTR.VELO")
            mres = 0.1
            vmax = 1
            velo = 0.5
            self.mock_axis_pvs[mres_pv] = mres
            self.mock_axis_pvs[vmax_pv] = vmax
            self.mock_axis_pvs[velo_pv] = velo
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
