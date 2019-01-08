from ReflectometryServer.footprint_calc import *
from ReflectometryServer.ChannelAccess.pv_manager import FP_SP_SUFFIX, FP_SP_RBV_SUFFIX, FP_RBV_SUFFIX

NOT_A_NUMBER = "NaN"


class FootprintManager(object):
    """
    Holds instances of the footprint calculator and manages access to them.
    """
    def __init__(self, footprint_setup):
        """
        :param footprint_setup(ReflectometryServer.footprint_calc.FootprintSetup): The beamline parameters relevant for
        the footprint calculation.
        """
        self._footprint_setup = footprint_setup
        self._footprint_calc_sp = FootprintCalculatorSetpoint(footprint_setup)
        self._footprint_calc_sp_rbv = FootprintCalculatorSetpointReadback(footprint_setup)
        self._footprint_calc_rbv = FootprintCalculatorReadback(footprint_setup)

    def get_footprint(self, sort):
        """
        Return the (penumbra) footprint at the sample for a given sort of value.

        :param sort: The type of value for which to calculate the footprint.
        :return: The footprint in mm
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_footprint()
        except (ZeroDivisionError, TypeError):
            return NOT_A_NUMBER

    def get_resolution(self, sort):
        """
        Return the minimum resolution of the beamline for a given sort of value.

        :param sort: The type of value for which to calculate the beamline resolution.
        :return: The resolution in mm
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_min_resolution()
        except (ZeroDivisionError, TypeError):
            return NOT_A_NUMBER

    def get_q_min(self, sort):
        """
        Get the minimum measurable Q value for a given sort of value.

        :param sort: The type of value for which to calculate the minimum Q
        :return: The minimum Q
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_q_min()
        except (ZeroDivisionError, TypeError):
            return NOT_A_NUMBER

    def get_q_max(self, sort):
        """
        Get the maximum measurable Q value for a given sort of value.

        :param sort: The type of value for which to calculate the maximum Q
        :return: The maximum Q
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_q_max()
        except (ZeroDivisionError, TypeError):
            return NOT_A_NUMBER

    def set_sample_length(self, value):
        """
        Set the length of the current sample.

        :param value: The length of the sample.
        """
        self._footprint_setup.gaps[SA] = value

    def get_sample_length(self):
        """
        :return: The currently set sample length
        """
        return self._footprint_setup.gaps[SA]

    def _get_footprint_calc_by_sort(self, type):
        """
        Returns a footprint calculator instance based on type of value.

        :param type: The type of value (setpoint, setpoint readback or readback)
        :return: A footprint calculator.
        """
        if type is FP_SP_SUFFIX:
            return self._footprint_calc_sp
        elif type is FP_SP_RBV_SUFFIX:
            return self._footprint_calc_sp_rbv
        else:
            return self._footprint_calc_rbv
