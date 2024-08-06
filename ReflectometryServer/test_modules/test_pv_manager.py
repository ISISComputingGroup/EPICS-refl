import unittest

from hamcrest import *
from server_common.utilities import convert_from_json, dehex_and_decompress

from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.ChannelAccess.pv_manager import PARAM_INFO_LOOKUP, PVManager
from ReflectometryServer.components import Component
from ReflectometryServer.geometry import ChangeAxis, PositionAndAngle
from ReflectometryServer.parameters import AxisParameter, BeamlineParameterGroup


class TestDriverUtils(unittest.TestCase):

    def setUp(self) -> None:
        self.comp = Component("comp", PositionAndAngle(0, 0, 0))

    def create_beamline(self, param):
        bl = Beamline([], [param], [], [BeamlineMode("mode", [])])
        pvmanager = PVManager()
        pvmanager.set_beamline(bl)

        return pvmanager

    def test_GIVEN_axis_param_with_characteristic_value_WHEN_create_beamline_THEN_param_info_contains_value(self):
        expected_characteristic_value = "MOT:MTR0101.RBV"
        param = AxisParameter("MYVALUE", self.comp, ChangeAxis.POSITION,
                              characteristic_value=expected_characteristic_value)
        pvmanager = self.create_beamline(param)

        pv_definition = pvmanager.PVDB[PARAM_INFO_LOOKUP[BeamlineParameterGroup.COLLIMATION_PLANE]]
        pv_value = convert_from_json(dehex_and_decompress(pv_definition["value"]))

        assert_that(pv_value[0], has_entry("characteristic_value", expected_characteristic_value))

    def test_GIVEN_axis_param_with_NO_characteristic_value_WHEN_create_beamline_THEN_param_info_contains_empty_value(self):
        param = AxisParameter("MYVALUE", self.comp, ChangeAxis.POSITION)
        pvmanager = self.create_beamline(param)

        pv_definition = pvmanager.PVDB[PARAM_INFO_LOOKUP[BeamlineParameterGroup.COLLIMATION_PLANE]]
        pv_value = convert_from_json(dehex_and_decompress(pv_definition["value"]))

        assert_that(pv_value[0], has_entry("characteristic_value", ""))

    def test_GIVEN_axis_param_with_description_WHEN_create_beamline_THEN_param_info_contains_description(self):
        expected_description = "MOT:MTR0101.RBV"
        param = AxisParameter("MYVALUE", self.comp, ChangeAxis.POSITION,
                              description=expected_description)
        pvmanager = self.create_beamline(param)

        pv_definition = pvmanager.PVDB[PARAM_INFO_LOOKUP[BeamlineParameterGroup.COLLIMATION_PLANE]]
        pv_value = convert_from_json(dehex_and_decompress(pv_definition["value"]))

        assert_that(pv_value[0], has_entry("description", expected_description))

    def test_GIVEN_axis_param_with_sp_mirrors_rbv_WHEN_create_beamline_THEN_sp_no_action_disp_is_1(self):
        expected_value = 1
        param_name = "MYVALUE"
        param = AxisParameter(param_name, self.comp, ChangeAxis.POSITION, sp_mirrors_rbv=True)
        pvmanager = self.create_beamline(param)

        pv_definition = pvmanager.PVDB[f"PARAM:{param_name}:SP_NO_ACTION.DISP"]
        pv_value = pv_definition["value"]

        assert_that(pv_value, is_(expected_value))


if __name__ == '__main__':
    unittest.main()
