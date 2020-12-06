import unittest
from collections import OrderedDict

from math import tan, radians, sqrt
from hamcrest import *
from parameterized import parameterized

from ReflectometryServer.axis import DirectCalcAxis
from ReflectometryServer.beam_path_calc import InBeamManager
from ReflectometryServer.geometry import ChangeAxis


class TestInBeamManager(unittest.TestCase):

    def set_up_beam_manager(self, current_parking_axis, axis_park_indexs=None, number_of_axes=1, axis_park_sequence_counts=None):
        axes_rbv = {}
        axes_rbv_list = []
        axes_sp = {}
        axes_sp_list = []
        if axis_park_indexs is None:
            axis_park_indexs = [current_parking_axis] * number_of_axes
        for axis_park_index, change_axis in zip(axis_park_indexs, list(ChangeAxis)[:number_of_axes]):
            axis_rbv = DirectCalcAxis(change_axis)
            axis_rbv.park_sequence_count = axis_park_index
            axes_rbv[change_axis] = axis_rbv
            axes_rbv_list.append(axis_rbv)
            axis_sp = DirectCalcAxis(change_axis)
            axis_sp.park_sequence_count = axis_park_index
            axes_sp[change_axis] = axis_sp
            axes_sp_list.append(axis_sp)
        beam_manager_rbv = InBeamManager()
        beam_manager_rbv.add_axes(axes_rbv)
        beam_manager_sp = InBeamManager()
        beam_manager_sp.add_axes(axes_sp)
        beam_manager_sp.parking_index = current_parking_axis
        beam_manager_sp.add_rbv_in_beam_manager(beam_manager_rbv)

        if axis_park_sequence_counts is None:
            axis_park_sequence_counts = [1] * number_of_axes
        for axis_rbv, axis_sp, park_sequence_count in zip(axes_rbv_list, axes_sp_list, axis_park_sequence_counts):
            axis_rbv.park_sequence_count = park_sequence_count
            axis_sp.park_sequence_count = park_sequence_count
        return axes_rbv_list, beam_manager_sp

    def test_GIVEN_in_beam_manager_with_one_axis_parking_starting_in_beam_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_updated(self):

        current_parking_axis = 0
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[None], axis_park_sequence_counts=[4])

        beam_manager_sp.set_is_in_beam(False)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis + 1))

    def test_GIVEN_in_beam_manager_with_one_axis_parking_starting_at_first_park_postion_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_updated(self):

        current_parking_axis = 1
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[0])

        beam_manager_sp.set_is_in_beam(False)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis + 1))

    def test_GIVEN_in_beam_manager_with_one_axis_parking_starting_at_last_park_postion_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_not_updated_updated(self):

        current_parking_axis = 1
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[0], axis_park_sequence_counts=[current_parking_axis+1])

        beam_manager_sp.set_is_in_beam(False)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_with_one_axis_component_unparking_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_updated(self):

        current_parking_axis = 2
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[3])

        beam_manager_sp.set_is_in_beam(True)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis - 1))

    def test_GIVEN_in_beam_manager_with_one_axis_component_unparking_last_step_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_updated_to_None(self):
        current_parking_axis = 0
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[1], axis_park_sequence_counts=[2])

        beam_manager_sp.set_is_in_beam(True)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(None))

    def test_GIVEN_in_beam_manager_with_one_axis_component_unparking_at_end_of_sequence_WHEN_axis_finishing_sequence_THEN_beam_manager_sp_sequence_is_not_updated(self):
        current_parking_axis = None
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[0], axis_park_sequence_counts=[2])

        beam_manager_sp.set_is_in_beam(True)
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(None))

    def test_GIVEN_in_beam_manager_with_one_axis_WHEN_axis_finishing_different_sequence_THEN_beam_manager_sp_sequence_is_not_updated(self):

        current_parking_axis = 1
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis)

        beam_manager_sp.set_is_in_beam(True)
        axis[0].parking_index = current_parking_axis + 1

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_with_one_axis_WHEN_axis_finishing_un_parked_THEN_beam_manager_sp_sequence_is_not_updated(self):
        current_parking_axis = 1
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis)

        axis[0].parking_index = None

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_with_two_axis_WHEN_one_axis_at_end_one_not_THEN_beam_manager_sp_sequence_is_not_updated(self):
        current_parking_axis = 0
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[None, None],
                                                         number_of_axes=2)

        beam_manager_sp.set_is_in_beam(False)
        axis[0].parking_index = None
        axis[1].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_with_two_axis_WHEN_one_axis_at_end_one_not_other_way_round_THEN_beam_manager_sp_sequence_is_not_updated(self):
        current_parking_axis = 0
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[None, None],
                                                         number_of_axes=2)

        beam_manager_sp.set_is_in_beam(False)
        axis[1].parking_index = None
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_with_two_axis_WHEN_both_axis_at_end_THEN_beam_manager_sp_sequence_is_updated(self):
        current_parking_axis = 1
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, axis_park_indexs=[0, 0], number_of_axes=2)

        beam_manager_sp.set_is_in_beam(False)
        axis[1].parking_index = current_parking_axis
        axis[0].parking_index = current_parking_axis

        assert_that(beam_manager_sp.parking_index, is_(current_parking_axis + 1))

    def test_GIVEN_in_beam_manager_is_in_WHEN_set_out_THEN_goes_to_first_parking_sequence(self):
        current_parking_axis = None
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, number_of_axes=2)

        beam_manager_sp.set_is_in_beam(False)
        result = beam_manager_sp.parking_index

        assert_that(result, is_(0))

    def test_GIVEN_in_beam_manager_is_already_out_WHEN_set_out_THEN_parking_sequence_not_reset(self):
        current_parking_axis = 2
        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, number_of_axes=2)

        beam_manager_sp.set_is_in_beam(False)
        result = beam_manager_sp.parking_index

        assert_that(result, is_(current_parking_axis))

    def test_GIVEN_in_beam_manager_is_out_WHEN_set_in_THEN_goes_to_first_parking_sequence(self):
        park_sequence_count = [5]
        current_parking_axis = park_sequence_count[0] - 1

        axis, beam_manager_sp = self.set_up_beam_manager(current_parking_axis, number_of_axes=1, axis_park_sequence_counts=park_sequence_count)

        beam_manager_sp.set_is_in_beam(True)
        result = beam_manager_sp.parking_index

        assert_that(result, is_(park_sequence_count[0] - 2))


if __name__ == '__main__':
    unittest.main()


