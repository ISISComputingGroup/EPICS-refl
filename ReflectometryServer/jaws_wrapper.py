from genie_python.channel_access_exceptions import UnableToConnectToPVException
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
        self._sp_pv = "{}:SP".format(self._rbv_pv)
        self._after_sp_change_listeners = set()
        self._after_rbv_change_listeners = set()
        try:
            CaChannelWrapper.add_monitor(self._rbv_pv, self._trigger_after_rbv_value_change_listeners)
            logger.debug("Monitoring {} for changes.".format(self._rbv_pv))
            CaChannelWrapper.add_monitor(self._sp_pv, self._trigger_after_sp_value_change_listeners)
            logger.debug("Monitoring {} for changes.".format(self._sp_pv))
        except UnableToConnectToPVException as e:
            logger.error("Error adding monitor: PV does not exist: {}".format(e))

    def _trigger_after_sp_value_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggered after setpoint readback value change listeners {}.".format(new_value))
        for value_change_listener in self._after_sp_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    def _trigger_after_rbv_value_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggered after setpoint readback value change listeners {}.".format(new_value))
        for value_change_listener in self._after_rbv_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    def add_after_sp_value_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_sp_change_listeners.add(listener)

    def add_after_rbv_value_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_rbv_change_listeners.add(listener)

    @property
    def sp(self):
        """
        Returns: the value of the underlying PV
        """
        try:
            return CaChannelWrapper.get_pv_value(self._sp_pv)
        except UnableToConnectToPVException:
            logger.error("Error reading value from {}: PV does not exist".format(self._sp_pv))
            return None

    @sp.setter
    def sp(self, value):
        """
        Writes a value to the underlying PV's VAL field.
        Args:
            value: The value to set
        """
        try:
            CaChannelWrapper.set_pv_value(self._sp_pv, value)
        except UnableToConnectToPVException:
            logger.error("Error writing value to {}: PV does not exist".format(self._sp_pv))
            return None
