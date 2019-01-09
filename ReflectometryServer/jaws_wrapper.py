from genie_python.genie_cachannel_wrapper import CaChannelWrapper

from ReflectometryServer.ChannelAccess.constants import MYPVPREFIX
import logging

logger = logging.getLogger(__name__)


class JawsWrapper(object):
    """
    Wrap a slit gap pv.
    """
    def __init__(self, pv_name):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        Args:
            pv_name (string): The name of the PV
        """
        self._rbv_pv = "{}{}".format(MYPVPREFIX, pv_name)
        self._sp_rbv_pv = "{}:SP:RBV".format(self._rbv_pv)
        self._after_rbv_change_listeners = set()
        self._after_sp_rbv_change_listeners = set()

        logger.debug("Monitoring {} for changes.".format(self._rbv_pv))
        logger.debug("Monitoring {} for changes.".format(self._sp_rbv_pv))
        CaChannelWrapper.add_monitor(self._sp_rbv_pv, self._trigger_after_value_change_listeners)

    def _trigger_after_value_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggered after setpoint readback value change listeners {}.".format(new_value))
        for value_change_listener in self._after_sp_rbv_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    def add_after_value_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_sp_rbv_change_listeners.add(listener)

    @property
    def sp_rbv(self):
        """
        Returns: the value of the underlying PV
        """
        return CaChannelWrapper.get_pv_value(self._sp_rbv_pv)

    @sp_rbv.setter
    def sp_rbv(self, value):
        """
        Writes a value to the underlying PV's VAL field.
        Args:
            value: The value to set
        """
        CaChannelWrapper.set_pv_value(self._sp_rbv_pv, value)

    @property
    def rbv(self):
        """
        Returns: the value of the underlying PV
        """
        return CaChannelWrapper.get_pv_value(self._rbv_pv)
