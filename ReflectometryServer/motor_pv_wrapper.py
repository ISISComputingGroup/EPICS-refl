"""
Wrapper for motor PVs
"""
from genie_python.genie_cachannel_wrapper import CaChannelWrapper

# Export these with better names
from CaChannel._ca import AlarmSeverity
from CaChannel._ca import AlarmCondition as AlarmStatus


from ReflectometryServer.ChannelAccess.constants import MYPVPREFIX
import logging

logger = logging.getLogger(__name__)


class MotorPVWrapper(object):
    """
    Wrap the motor pvs to allow easy access to all motor pv values needed.
    """
    def __init__(self, pv_name):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        :param pv_name (string): The name of the PV
        """
        self._pv_name = "{}{}".format(MYPVPREFIX, pv_name)
        self._after_value_change_listeners = set()

        rbv_pv = "{}.RBV".format(self._pv_name)
        logger.debug("Monitoring {} for changes.".format(rbv_pv))
        CaChannelWrapper.add_monitor(rbv_pv, self._trigger_after_height_change_listeners)

    def _trigger_after_height_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggered after height change listeners {}.".format(new_value))
        for value_change_listener in self._after_value_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    def add_after_value_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state

        """
        self._after_value_change_listeners.add(listener)

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
        Returns: the value of the underlying velocity PV
        """
        return CaChannelWrapper.get_pv_value(self._pv_name + ".VELO")

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.
        Args:
            value: The value to set
        """
        CaChannelWrapper.set_pv_value(self._pv_name + ".VELO", value)

    @property
    def max_velocity(self):
        """
        Returns: the value of the underlying max velocity PV
        """
        return CaChannelWrapper.get_pv_value(self._pv_name + ".VMAX")
