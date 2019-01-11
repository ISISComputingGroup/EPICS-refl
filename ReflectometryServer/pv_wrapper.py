"""
Wrapper for motor PVs
"""
from genie_python.genie_cachannel_wrapper import CaChannelWrapper
from genie_python.channel_access_exceptions import UnableToConnectToPVException

# Export these with better names
from CaChannel._ca import AlarmSeverity
from CaChannel._ca import AlarmCondition as AlarmStatus


from ReflectometryServer.ChannelAccess.constants import MYPVPREFIX
import logging

logger = logging.getLogger(__name__)


class PVWrapper(object):
    def __init__(self, base_pv):
        """
        Creates a wrapper around a PV.

        Args:
            base_pv(String): The name of the PV
        """
        self._prefixed_pv = "{}{}".format(MYPVPREFIX, base_pv)
        self._set_pvs()

        self._after_rbv_change_listeners = set()
        self._after_sp_change_listeners = set()

    def _set_pvs(self):
        self._rbv_pv = ""
        self._sp_pv = ""

    @staticmethod
    def _monitor_pv(pv, call_back_function):
        """
        Adds a monitor function to a given PV.

        Args:
            pv(String): The pv to monitor
            call_back_function: The function to execute on a pv value change
        """
        if CaChannelWrapper.pv_exists(pv):
            CaChannelWrapper.add_monitor(pv, call_back_function)
            logger.debug("Monitoring {} for changes.".format(pv))
        else:
            logger.error("Error adding monitor to {}: PV does not exist".format(pv))

    @staticmethod
    def _read_pv(pv):
        """
        Read the value from a given PV.

        Args:
            pv(String): The pv to read
        """
        try:
            return CaChannelWrapper.get_pv_value(pv)
        except UnableToConnectToPVException:
            logger.error("Error reading value from {}: PV does not exist".format(pv))
            return None

    @staticmethod
    def _write_pv(pv, value):
        """
        Write a value to a given PV.

        Args:
            pv(String): The PV to write to
            value: The new value
        """
        try:
            CaChannelWrapper.set_pv_value(pv, value)
        except UnableToConnectToPVException:
            logger.error("Error writing value to {}: PV does not exist".format(pv))

    def add_after_rbv_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state

        """
        self._after_rbv_change_listeners.add(listener)

    def _trigger_after_rbv_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggering after value change listeners. New value: {}.".format(new_value))
        for value_change_listener in self._after_rbv_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    def add_after_sp_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_sp_change_listeners.add(listener)

    def _trigger_after_sp_change_listeners(self, new_value, alarm_severity, alarm_status):
        logger.debug("Triggered after setpoint readback value change listeners {}.".format(new_value))
        for value_change_listener in self._after_sp_change_listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    @property
    def name(self):
        """
        Returns: the name of the underlying PV
        """
        return self._prefixed_pv

    @property
    def sp(self):
        """
        Returns: the value of the underlying PV
        """
        return self._read_pv(self._sp_pv)

    @sp.setter
    def sp(self, value):
        """
        Writes a value to the underlying PV's VAL field.
        Args:
            value: The value to set
        """
        self._write_pv(self._sp_pv, value)


class MotorPVWrapper(PVWrapper):
    """
    Wrap the motor PVs to allow easy access to all motor PV values needed.
    """
    def __init__(self, base_pv):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        :param pv_name (string): The name of the PV
        """
        super(MotorPVWrapper, self).__init__(base_pv)

        self._monitor_pv(self._rbv_pv, self._trigger_after_rbv_change_listeners)

    def _set_pvs(self):
        self._sp_pv = self._prefixed_pv
        self._rbv_pv = "{}.RBV".format(self._prefixed_pv)

    @property
    def velocity(self):
        """
        Returns: the value of the underlying velocity PV
        """
        return CaChannelWrapper.get_pv_value(self._prefixed_pv + ".VELO")

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.

        Args:
            value: The value to set
        """
        CaChannelWrapper.set_pv_value(self._prefixed_pv + ".VELO", value)

    @property
    def max_velocity(self):
        """
        Returns: the value of the underlying max velocity PV
        """
        return CaChannelWrapper.get_pv_value(self._prefixed_pv + ".VMAX")


class AxisPVWrapper(PVWrapper):
    """
    Wrap the axis PVs on top of a motor record to allow easy access to all axis PV values needed.
    """
    def __init__(self, base_pv):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        Args:
            pv_name (string): The name of the PV
        """
        super(AxisPVWrapper, self).__init__(base_pv)

        self._monitor_pv(self._sp_pv, self._trigger_after_sp_change_listeners)
        self._monitor_pv(self._rbv_pv, self._trigger_after_rbv_change_listeners)

    def _set_pvs(self):
        self._sp_pv = "{}:SP".format(self._prefixed_pv)
        self._rbv_pv = self._prefixed_pv
