import unittest

from hamcrest import *
from mock import patch
from parameterized import parameterized

from ReflectometryServer import *
from ReflectometryServer.beamline import ActiveModeUpdate
from ReflectometryServer.test_modules.data_mother import create_mock_axis
from ReflectometryServer.test_modules.test_engineering_corrections import MockBeamline


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
        expected1 = Component("1", PositionAndAngle(0, 10, 90))
        expected2 = Component("2", PositionAndAngle(0, 20, 90))
        expected3 = Component("3", PositionAndAngle(0, 30, 90))

        add_component(expected1)
        add_component(expected2)
        add_component(expected3)

        result = get_configured_beamline()

        assert_that(ConfigHelper.components, only_contains(expected1, expected2, expected3))

    def test_GIVEN_no_parameters_added_WHEN_get_beamline_THEN_parameters_are_empty(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.parameters, is_([]))

    def test_GIVEN_beam_line_parameter_added_WHEN_get_beamline_THEN_beam_line_has_parameter(self):
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        expected1 = AxisParameter("param1", comp1, ChangeAxis.POSITION)

        comp2 = Component("2", PositionAndAngle(0, 0, 2))
        expected2 = AxisParameter("param2", comp1, ChangeAxis.POSITION)

        add_component(comp1)
        add_component(comp2)
        add_parameter(expected1)
        add_parameter(expected2)

        result = get_configured_beamline()

        assert_that(ConfigHelper.parameters, only_contains(expected1, expected2))
        assert_that(result.parameters.values(), only_contains(expected1, expected2))

    def test_GIVEN_no_mode_added_WHEN_get_beamline_THEN_modes_are_empty(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.modes, is_([]))

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
        expected1 = AxisParameter(expected_name1, comp1, ChangeAxis.POSITION)

        mode = add_mode("mode1")
        add_component(comp1)
        add_parameter(expected1, modes=[mode])

        result = get_configured_beamline()

        assert_that(result.get_param_names_in_mode(), only_contains(expected_name1))

    def test_GIVEN_multiple_parameter_with_modes_WHEN_get_beamline_THEN_parameter_in_given_mode(self):
        param_name1 = "param1"
        param_name2 = "param2"
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        param1 = AxisParameter(param_name1, comp1, ChangeAxis.POSITION)
        param2 = AxisParameter(param_name2, comp1, ChangeAxis.POSITION)

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
        param1 = AxisParameter(param_name1, comp1, ChangeAxis.POSITION)
        param2 = AxisParameter(param_name2, comp1, ChangeAxis.POSITION)

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
        expected1 = AxisParameter(expected_name1, comp1, ChangeAxis.POSITION)

        mode = add_mode("mode1")
        add_component(comp1)
        add_parameter(expected1, mode, [(mode, expected_init)])

        result = ConfigHelper.mode_initial_values[mode]

        assert_that(result, has_entry(expected_name1, expected_init))

    def test_GIVEN_no_driver_added_WHEN_get_beamline_THEN_drivers_are_empty(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.drivers, is_([]))

    def test_GVIEN_add_driver_WHEN_get_beamline_THEN_driver_added(self):
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        driver = IocDriver(comp1, ChangeAxis.POSITION, create_mock_axis("MOT0101", 1, 1))
        add_driver(driver)

        result = get_configured_beamline()

        assert_that(result.drivers, only_contains(driver))

    def test_GVIEN_add_slits_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_wrapper_mock:

            add_slit_parameters(1)

            result = ConfigHelper.parameters

            assert_that([parameter.name for parameter in result], contains_inanyorder("S1VG", "S1HG"))

            assert_that([call[0][0] for call in jaws_wrapper_mock.call_args_list], only_contains("MOT:JAWS1"))
            assert_that([call[0][1] for call in jaws_wrapper_mock.call_args_list], contains_exactly(True, False))
            assert_that([call[0][2] for call in jaws_wrapper_mock.call_args_list], contains_exactly(True, True))

    def test_GVIEN_add_slits_and_gaps_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_and_centres_exist(self):

        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_wrapper_mock:

            add_slit_parameters(1, include_centres=True)

            result = ConfigHelper.parameters

            assert_that([parameter.name for parameter in result], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))

            assert_that([call[0][0] for call in jaws_wrapper_mock.call_args_list], only_contains("MOT:JAWS1"))
            assert_that([call[0][1] for call in jaws_wrapper_mock.call_args_list], contains(True, True, False, False))
            assert_that([call[0][2] for call in jaws_wrapper_mock.call_args_list], contains(True, False, True, False))


    def test_GVIEN_add_slits_and_gaps_into_modes_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):
        mode = add_mode("mode")
        mode1 = add_mode("mode1")
        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver"):

            add_slit_parameters(1, modes=[mode, mode1], include_centres=True)

        result = ConfigHelper.mode_params

        assert_that(result[mode], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))
        assert_that(result[mode1], contains_inanyorder("S1VG", "S1VC", "S1HG", "S1HC"))

    def test_GVIEN_add_slits_and_gaps_excluding_VC_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist_except_VC(self):

        with patch("ReflectometryServer.config_helper.create_jaws_pv_driver"):

            add_slit_parameters(1, exclude="VC", include_centres=True)

        result = ConfigHelper.parameters

        assert_that([parameter.name for parameter in result], contains_inanyorder("S1VG", "S1HG", "S1HC"))

    def test_GVIEN_add_slits_with_beam_blocker_N_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_blade_pv_driver") as blade_drivers:
            with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_driver:

                add_slit_parameters(1, beam_blocker="N")

                result = ConfigHelper.parameters

                assert_that([parameter.name for parameter in result], contains_inanyorder("S1VG", "S1HG", "S1BLOCK", "S1N", "S1S"))

                assert_that([call[0][0] for call in blade_drivers.call_args_list], only_contains("MOT:JAWS1"))
                assert_that([call[0][1] for call in blade_drivers.call_args_list], contains_exactly("N", "S"))

    def test_GVIEN_add_slits_with_beam_blocker_S_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_blade_pv_driver") as blade_drivers:
            with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_driver:

                add_slit_parameters(1, beam_blocker="S")

                result = ConfigHelper.parameters

                parameters = {parameter.name: parameter for parameter in result}
                assert_that(parameters.keys(), contains_inanyorder("S1VG", "S1HG", "S1BLOCK", "S1N", "S1S"))
                assert_that(parameters["S1BLOCK"].options, contains_inanyorder("No", "South"))

                assert_that([call[0][0] for call in blade_drivers.call_args_list], only_contains("MOT:JAWS1"))
                assert_that([call[0][1] for call in blade_drivers.call_args_list], contains_exactly("N", "S"))

    def test_GVIEN_add_slits_with_beam_blocker_E_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_blade_pv_driver") as blade_drivers:
            with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_driver:

                add_slit_parameters(1, beam_blocker="E")

                result = ConfigHelper.parameters

                parameters = {parameter.name: parameter for parameter in result}
                assert_that(parameters.keys(), contains_inanyorder("S1VG", "S1HG", "S1BLOCK", "S1E", "S1W"))
                assert_that(parameters["S1BLOCK"].options, contains_inanyorder("No", "East"))

                assert_that([call[0][0] for call in blade_drivers.call_args_list], only_contains("MOT:JAWS1"))
                assert_that([call[0][1] for call in blade_drivers.call_args_list], contains_exactly("E", "W"))

    def test_GVIEN_add_slits_with_beam_blocker_EN_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_blade_pv_driver") as blade_drivers:
            with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_driver:

                add_slit_parameters(1, beam_blocker="EN")

                result = ConfigHelper.parameters

                parameters = {parameter.name: parameter for parameter in result}
                assert_that(parameters.keys(), contains_inanyorder("S1VG", "S1HG", "S1BLOCK", "S1E", "S1W", "S1S", "S1N"))
                assert_that(parameters["S1BLOCK"].options, contains_inanyorder("No", "East", "North"))

                assert_that([call[0][0] for call in blade_drivers.call_args_list], only_contains("MOT:JAWS1"))
                assert_that([call[0][1] for call in blade_drivers.call_args_list], contains_inanyorder("N", "S", "E", "W"))

    def test_GVIEN_add_slits_with_beam_blocker_EN_and_exclude_W_WHEN_get_parameters_in_config_THEN_parameters_for_all_slit_gaps_exist(self):

        with patch("ReflectometryServer.config_helper.create_blade_pv_driver") as blade_drivers:
            with patch("ReflectometryServer.config_helper.create_jaws_pv_driver") as jaws_driver:

                add_slit_parameters(1, beam_blocker="EN", exclude=["W"])

                result = ConfigHelper.parameters

                parameters = {parameter.name: parameter for parameter in result}
                assert_that(parameters.keys(), contains_inanyorder("S1VG", "S1HG", "S1BLOCK", "S1E", "S1S", "S1N"))
                assert_that(parameters["S1BLOCK"].options, contains_inanyorder("No", "East", "North"))

                assert_that([call[0][0] for call in blade_drivers.call_args_list], only_contains("MOT:JAWS1"))
                assert_that([call[0][1] for call in blade_drivers.call_args_list], contains_inanyorder("N", "S", "E"))

    def test_GIVEN_no_beam_start_added_WHEN_get_beamline_THEN_beamstart_is_none(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.beam_start, is_(None))

    def test_GVIEN_add_beam_start_WHEN_get_beamline_THEN_beam_start_is_correct(self):
        add_mode("NR")
        expected_beam_start = PositionAndAngle(0.0, -10.0, 0.0)
        comp = add_component(Component("name", PositionAndAngle(0, 0, 90)))
        add_beam_start(expected_beam_start)

        result = get_configured_beamline()

        assert_that(comp.beam_path_set_point.get_outgoing_beam(), is_(expected_beam_start))

    def test_GIVEN_no_footprint_added_WHEN_get_beamline_THEN_footprint_is_none(self):

        result = get_configured_beamline()

        assert_that(ConfigHelper.footprint_setup, is_(None))

    def test_GVIEN_add_footprint_setup_WHEN_get_beamline_THEN_beam_start_is_correct(self):
        add_mode("NR")
        comp = add_component(Component("name", PositionAndAngle(0, 1, 90)))
        param = AxisParameter("name", comp, ChangeAxis.POSITION)
        expected_sample_length = 10

        footprint = add_footprint_setup(FootprintSetup(1, 2, 3, 4, 5, param, param, param, param, param, -1, 1))
        footprint.sample_length = expected_sample_length

        result = get_configured_beamline()
        assert_that(result.footprint_manager.get_sample_length(), is_(expected_sample_length))

    def test_GIVEN_beam_line_parameter_driver_and_component_added_at_marker_WHEN_get_parameters_THEN_inserted_at_right_place(self):
        comp1 = Component("1", PositionAndAngle(0, 0, 1))
        expected1 = AxisParameter("param1", comp1, ChangeAxis.POSITION)
        driver1 = IocDriver(comp1, ChangeAxis.POSITION, create_mock_axis("MOT0101", 1, 1))

        comp2 = Component("2", PositionAndAngle(0, 0, 2))
        expected2 = AxisParameter("param2", comp2, ChangeAxis.POSITION)
        driver2 = IocDriver(comp2, ChangeAxis.POSITION, create_mock_axis("MOT0102", 1, 1))

        comp3 = Component("2", PositionAndAngle(0, 0, 2))
        expected3 = AxisParameter("param3", comp3, ChangeAxis.POSITION)
        driver3 = IocDriver(comp3, ChangeAxis.POSITION, create_mock_axis("MOT0103", 1, 1))

        add_component(comp1)
        add_parameter(expected1)
        add_driver(driver1)

        comp_marker = add_component_marker()
        param_marker = add_parameter_marker()
        driver_marker = add_driver_marker()

        add_parameter(expected3)
        add_component(comp3)
        add_driver(driver3)

        add_component(comp2, marker=comp_marker)
        add_parameter(expected2, marker=param_marker)
        add_driver(driver2, marker=driver_marker)

        assert_that(ConfigHelper.parameters, contains(expected1, expected2, expected3))
        assert_that(ConfigHelper.drivers, contains(driver1, driver2, driver3))
        assert_that(ConfigHelper.components, contains(comp1, comp2, comp3))

    def test_GIVEN_optional_is_not_set_WHEN_checking_optional_is_set_THEN_return_false(self):
        macros = {}
        optional_id = 1
        expected = False

        actual = optional_is_set(optional_id, macros)

        assert_that(actual, is_(expected))

    @parameterized.expand([("True", True), ("false", False), ("Nonesense", False)])
    def test_GIVEN_optional_is_set_to_string_WHEN_checking_optional_is_set_THEN_return_expected_bool(self, string, expected):
        macros = {"OPTIONAL_1": string}
        optional_id = 1

        actual = optional_is_set(optional_id, macros)

        assert_that(actual, is_(expected))

    def test_WHEN_creating_mode_correction_with_helper_method_THEN_mode_select_correction_returned(self):
        correction = 1
        mode_name = "nr"

        result = as_mode_correction(correction, [mode_name])

        assert_that(result, instance_of(ModeSelectCorrection))

    def test_GIVEN_value_and_mode_WHEN_creating_mode_correction_with_helper_method_THEN_default_correction_is_0(self):
        correction = 1
        mode_name = "nr"
        mode_correction = as_mode_correction(correction, [mode_name])

        result = mode_correction.init_from_axis(0)

        assert_that(result, is_(0))

    def test_GIVEN_value_and_mode_WHEN_creating_mode_correction_with_helper_method_THEN_correction_in_mode_behaves_correctly(self):
        correction = 1
        mode_name = "nr"
        mock_beamline = MockBeamline()
        mode_correction = as_mode_correction(correction, [mode_name])
        mode_correction.set_observe_mode_change_on(mock_beamline)

        mock_beamline.trigger_listeners(ActiveModeUpdate(BeamlineMode(mode_name, [])))
        result = mode_correction.init_from_axis(0)

        assert_that(result, is_(correction * (-1)))  # correction is subtracted


if __name__ == '__main__':
    unittest.main()
