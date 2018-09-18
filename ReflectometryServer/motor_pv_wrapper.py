"""
Wrapper for motor PVs
"""
from genie_python.genie_cachannel_wrapper import CaChannelWrapper


class MotorPVWrapper(object):
    """
    Wrap the motor pvs to allow easy access to all motor pv values needed.
    """
    def __init__(self, pv_name):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        :param pv_name (string): The name of the PV
        """
        self._pv_name = pv_name

    @property
    def name(self):
        """
        Returns: the name of the underlying PV
        """
        return self._pv_name

    @property
    def value(self):
        """
        Returns: the value of the underlying PV
        """
        return CaChannelWrapper.get_pv_value(self._pv_name)

    @value.setter
    def value(self, value):
        """
        Writes a value to the underlying PV's VAL field.
        Args:
            value: The value to set
        """
        CaChannelWrapper.set_pv_value(self._pv_name, value)

    @property
    def velocity(self):
        """
        Returns: the value of the underlying PV
        """
        return CaChannelWrapper.get_pv_value(self._pv_name + ".VMAX")

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying PV's VAL field.
        Args:
            value: The value to set
        """
        CaChannelWrapper.set_pv_value(self._pv_name + ".VELO", value)
