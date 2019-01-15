"""
Manager for the footprint calc.
"""

from ReflectometryServer.footprint_calc import *
from ReflectometryServer.ChannelAccess.pv_manager import FootprintSort


class FootprintManager(object):
    """
    Holds instances of the footprint calculator and manages access to them.
    """
    def __init__(self, footprint_setup):
        """
        Args:
            footprint_setup: The beamline parameters relevant for
                the footprint calculation.
        """
        self._footprint_setup = footprint_setup
        self._footprint_calc_sp = FootprintCalculatorSetpoint(footprint_setup)
        self._footprint_calc_sp_rbv = FootprintCalculatorSetpointReadback(footprint_setup)
        self._footprint_calc_rbv = FootprintCalculatorReadback(footprint_setup)

    def get_footprint(self, sort):
        """
        Return the (penumbra) footprint at the sample for a given sort of value.

        Args:
            sort: The type of value for which to calculate the footprint.

        Returns: The footprint in mm
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_footprint()
        except (ZeroDivisionError, KeyError, AttributeError):
            return float("NaN")

    def get_resolution(self, sort):
        """
        Return the minimum resolution of the beamline for a given sort of value.
        Args:
            sort: The type of value for which to calculate the beamline resolution.
        Returns: The resolution in mm
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_min_resolution()
        except (ZeroDivisionError, KeyError, AttributeError, ValueError):
            return float("NaN")

    def get_q_min(self, sort):
        """
        Get the minimum measurable Q value for a given sort of value.

        Args:
            sort: The type of value for which to calculate the minimum Q
        Returns: The minimum Q
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_q_min()
        except (ZeroDivisionError, KeyError, AttributeError):
            return float("NaN")

    def get_q_max(self, sort):
        """
        Get the maximum measurable Q value for a given sort of value.

        Args:
            sort: The type of value for which to calculate the maximum Q
        Returns: The maximum Q
        """
        footprint_calc = self._get_footprint_calc_by_sort(sort)
        try:
            return footprint_calc.calc_q_max()
        except (ZeroDivisionError, KeyError, AttributeError):
            return float("NaN")

    def set_sample_length(self, value):
        """
        Set the length of the current sample.

        Args:
            value: The length of the sample.
        """
        self._footprint_setup.sample_length = value

    def get_sample_length(self):
        """
        Returns: The currently set sample length
        """
        return self._footprint_setup.sample_length

    def _get_footprint_calc_by_sort(self, sort):
        """
        Returns a footprint calculator instance based on type of value.

        Args:
            sort: The type of value (setpoint, setpoint readback or readback)
        Returns: A footprint calculator.
        """
        if sort is FootprintSort.SP:
            return self._footprint_calc_sp
        elif sort is FootprintSort.SP_RBV:
            return self._footprint_calc_sp_rbv
        elif sort is FootprintSort.RBV:
            return self._footprint_calc_rbv
        return None
