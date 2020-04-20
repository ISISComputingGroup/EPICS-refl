import unittest

from hamcrest import *
from mock import patch
from ReflectometryServer import *
from ReflectometryServer.test_modules.data_mother import create_mock_axis


class TestConfigHelper(unittest.TestCase):
    def setUp(self):
        ConfigHelper.reset()

    def test_GIVEN_no_beam_line_constants_added_WHEN_get_beamline_and_config_helper_THEN_constants_are_empty(self):

        result = get_configured_beamline()

        assert_that(result.beamline_constants, is_([]))
        assert_that(ConfigHelper.constants, is_([]))

    def test_GIVEN_no_components_added_WHEN_get_beamline_THEN_components_are_empty(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.components, is_([]))

    def test_GIVEN_beam_line_constants_added_WHEN_get_beamline_THEN_beamline_has_constants(self):
        expected_constant1 = BeamlineConstant("1", 10, "constant 1")
        expected_constant2 = BeamlineConstant("2", 20.0, "constant 2")
        expected_constant3 = BeamlineConstant("constant 3", True, "constant 3")

        add_constant(expected_constant1)
        add_constant(expected_constant2)
        add_constant(expected_constant3)

        result = get_configured_beamline()

        assert_that(result.beamline_constants, only_contains(expected_constant1, expected_constant2, expected_constant3))

    def test_GIVEN_beam_line_components_added_WHEN_get_beamline_THEN_beam_line_has_components(self):
        expected1 = Component("1", PositionAndAngle(0, 0, 0))
        expected2 = Component("2", PositionAndAngle(0, 0, 0))
        expected3 = Component("3", PositionAndAngle(0, 0, 0))

        add_component(expected1)
        add_component(expected2)
        add_component(expected3)

        result = get_configured_beamline()

        assert_that(ConfigHelper.components, only_contains(expected1, expected2, expected3))

    def test_GIVEN_beam_line_parameter_added_WHEN_get_beamline_THEN_beam_line_has_parameter(self):
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        expected1 = TrackingPosition("param1", comp1)

        comp2 = Component("2", PositionAndAngle(0, 0, 2))
        expected2 = TrackingPosition("param2", comp1)

        add_component(comp1)
        add_component(comp2)
        add_parameter(expected1)
        add_parameter(expected2)

        result = get_configured_beamline()

        assert_that(ConfigHelper.parameters, only_contains(expected1, expected2))
        assert_that(result.parameters.values(), only_contains(expected1, expected2))

    def test_GIVEN_beam_line_mode_added_WHEN_get_beamline_THEN_beam_line_has_mode(self):
        expected_name1 = "mode1"
        expected_name2 = "mode2"
        expected_disabled = True

        add_mode(expected_name1)
        add_mode(expected_name2, is_disabled=expected_disabled)

        result = get_configured_beamline()

        assert_that(ConfigHelper.modes, only_contains(expected_name1, expected_name2))
        assert_that(ConfigHelper.mode_is_disabled[expected_name1], is_(False))
        assert_that(ConfigHelper.mode_is_disabled[expected_name2], is_(True))
        assert_that(result.mode_names, only_contains(expected_name1, expected_name2))

    def test_GIVEN_parameter_has_mode_WHEN_get_beamline_THEN_parameter_in_mode(self):
        expected_name1 = "param1"
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        expected1 = TrackingPosition(expected_name1, comp1)

        mode = add_mode("mode1")
        add_component(comp1)
        add_parameter(expected1, modes=[mode])

        result = get_configured_beamline()

        assert_that(result.get_param_names_in_mode(), only_contains(expected_name1))

    def test_GIVEN_multiple_parameter_with_modes_WHEN_get_beamline_THEN_parameter_in_given_mode(self):
        param_name1 = "param1"
        param_name2 = "param2"
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        param1 = TrackingPosition(param_name1, comp1)
        param2 = TrackingPosition(param_name2, comp1)

        add_component(comp1)
        mode1 = add_mode("mode1")
        mode2 = add_mode("mode2")

        add_parameter(param1, modes=[mode1, mode2])
        add_parameter(param2, [mode2])

        result = get_configured_beamline()
        result.active_mode = mode1
        assert_that(result.get_param_names_in_mode(), only_contains(param_name1))

        result.active_mode = mode2
        assert_that(result.get_param_names_in_mode(), only_contains(param_name1, param_name2))

    def test_GIVEN_multiple_parameter_with_modes_and_inits_WHEN_get_beamline_THEN_parameter_in_given_mode(self):
        param_name1 = "param1"
        param_name2 = "param2"
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        param1 = TrackingPosition(param_name1, comp1)
        param2 = TrackingPosition(param_name2, comp1)

        add_component(comp1)
        mode1 = add_mode("mode1")
        mode2 = add_mode("mod")

        add_parameter(param1, modes=[mode1, mode2], mode_inits=[(mode1, 0.0)])
        add_parameter(param2, mode2)

        result = get_configured_beamline()
        result.active_mode = mode1
        assert_that(result.get_param_names_in_mode(), only_contains(param_name1))

        result.active_mode = mode2
        assert_that(result.get_param_names_in_mode(), only_contains(param_name1, param_name2))

    def test_GIVEN_parameter_has_initial_value_WHEN_add_THEN_initial_values_added_to_mode(self):
        expected_init = 0.1
        expected_name1 = "param1"
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        expected1 = TrackingPosition(expected_name1, comp1)

        mode = add_mode("mode1")
        add_component(comp1)
        add_parameter(expected1, mode, [(mode, expected_init)])

        result = ConfigHelper.mode_initial_values[mode]

        assert_that(result, has_entry(expected_name1, expected_init))

    def test_GVIEN_add_driver_WHEN_get_beamline_THEN_driver_added(self):
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        driver = DisplacementDriver(comp1, create_mock_axis("MOT0101", 1, 1))
        add_driver(driver)

        result = get_configured_beamline()

        assert_that(result.drivers, only_contains(driver))

    def test_GVIEN_add_slits_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_wrapper_mock:

            add_slit_parameters(1)

        result = ConfigHelper.parameters

        assert_that([parameter.name for parameter in result], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))

        assert_that([call.args[0] for call in jaws_wrapper_mock.call_args_list], only_contains("MOT:JAWS1"))
        assert_that([call.args[1] for call in jaws_wrapper_mock.call_args_list], contains(True, True, False, False))
        assert_that([call.args[2] for call in jaws_wrapper_mock.call_args_list], contains(True, False, True, False))

    def test_GVIEN_add_slits_into_modes_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):
        mode = add_mode("mode")
        mode1 = add_mode("mode1")
        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_wrapper_mock:

            add_slit_parameters(1, modes=[mode, mode1])

        result = ConfigHelper.mode_params

        assert_that(result[mode], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))
        assert_that(result[mode1], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))

    def test_GVIEN_add_beam_start_WHEN_get_beamline_THEN_beam_start_is_correct(self):
        add_mode("NR")
        expected_beam_start = PositionAndAngle(0.0, -10.0, 0.0)
        comp = add_component(Component("name", PositionAndAngle(0, 0, 0)))
        add_beam_start(expected_beam_start)

        result = get_configured_beamline()

        assert_that(comp.beam_path_set_point.get_outgoing_beam(), is_(expected_beam_start))

    def test_GVIEN_add_footprint_setup_WHEN_get_beamline_THEN_beam_start_is_correct(self):
        add_mode("NR")
        comp = add_component(Component("name", PositionAndAngle(0, 1, 90)))
        param = TrackingPosition("name", comp)
        expected_sample_length = 10

        footprint = add_footprint_setup(FootprintSetup(1, 2, 3, 4, 5, param, param, param, param, param, -1, 1))
        footprint.sample_length = expected_sample_length

        result = get_configured_beamline()
        assert_that(result.footprint_manager.get_sample_length(), is_(expected_sample_length))


if __name__ == '__main__':
    unittest.main()
