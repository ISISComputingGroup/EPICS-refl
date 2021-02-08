import unittest

from hamcrest import *

from ReflectometryServer.ChannelAccess.pv_manager import PVManager, PARAM_INFO_LOOKUP
from ReflectometryServer.components import Component
from ReflectometryServer.geometry import PositionAndAngle, ChangeAxis
from ReflectometryServer.beamline import Beamline, BeamlineMode
from ReflectometryServer.parameters import AxisParameter, BeamlineParameterGroup
from server_common.utilities import dehex_and_decompress, convert_from_json


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


if __name__ == '__main__':
    unittest.main()
