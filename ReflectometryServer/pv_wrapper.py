"""
Wrapper for motor PVs
"""
from functools import partial

from ReflectometryServer.ChannelAccess.constants import MYPVPREFIX, MTR_MOVING, MTR_STOPPED
from ReflectometryServer.file_io import AutosaveType, read_autosave_value, write_autosave_value
import logging

from server_common.channel_access import ChannelAccess, UnableToConnectToPVException

logger = logging.getLogger(__name__)


class PVWrapper(object):
    """
    Wrap a single motor axis. Provides relevant listeners and synchronization utilities.
    """
    def __init__(self, base_pv, ca=None):
        """
        Creates a wrapper around a PV.

        Args:
            base_pv(String): The name of the PV
        """
        if ca is None:
            self._ca = ChannelAccess
        else:
            self._ca = ca
        self._name = base_pv
        self._prefixed_pv = "{}{}".format(MYPVPREFIX, base_pv)
        self._after_rbv_change_listeners = set()
        self._after_sp_change_listeners = set()
        self._after_is_changing_change_listeners = set()

        self._moving_state = None
        self._moving_direction = None
        self._velocity_cache_restored = None
        self._velocity_cache = None
        self._velocity = None
        self._backlash_distance = None
        self._backlash_velocity = None
        self.max_velocity = None

        self._set_pvs()
        self._set_resolution()
        self._set_max_velocity()

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis. Must be overridden in subclass.
        """
        self._rbv_pv = ""
        self._sp_pv = ""
        self._velo_pv = ""
        self._vmax_pv = ""
        self._dmov_pv = ""
        self._bdst_pv = ""
        self._bvel_pv = ""
        self._dir_pv = ""
        raise NotImplementedError()

    def _set_resolution(self):
        """
        Set the motor resolution for this axis. Must be overridden in subclass.
        """
        self._resolution = 0
        raise NotImplementedError()

    def _set_max_velocity(self):
        """
        Sets the maximum velocity this axis can move at.
        """
        self.max_velocity = self._read_pv(self._vmax_pv)

    def initialise(self):
        """
        Initialise PVWrapper values once the beamline is ready.
        """
        self._add_monitors()
        self._velocity = self._read_pv(self._velo_pv)
        self._backlash_distance = self._read_pv(self._bdst_pv)
        self._backlash_velocity = self._read_pv(self._bvel_pv)
        self._moving_direction = self._read_pv(self._dir_pv)
        self._init_velocity_cache()

    def _init_velocity_cache(self):
        if self._velocity_cache is None:
            try:
                # Explanation: autosave read can return the string '[value]' so strip square brackets
                autosave_value = read_autosave_value(self.name, AutosaveType.VELOCITY)
                if autosave_value[0] == "[":
                    autosave_value = autosave_value[1:-1]
                self._velocity_cache = float(autosave_value)
                logger.debug(
                    "_velocity_cache: PV: {}, value: {}, type: {}".format(self.name, self._velocity_cache, type(self._velocity_cache)))
                self._velocity_cache_restored = True
            except ValueError as error:
                logger.error("Error: Cache velocity of wrong type: {error_message}".format(error_message=error))
        if self._velocity_cache is None:
            logger.error("Error: _velocity_cache is None")
            self._velocity_cache = 0.0

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv,
                         partial(self._trigger_listeners, self._after_rbv_change_listeners))
        self._monitor_pv(self._sp_pv,
                         partial(self._trigger_listeners, self._after_sp_change_listeners))

        self._monitor_pv(self._dmov_pv, self._on_update_moving_state)
        self._monitor_pv(self._velo_pv, self._on_update_velocity)
        self._monitor_pv(self._bdst_pv, self._on_update_backlash_distance)
        self._monitor_pv(self._bvel_pv, self._on_update_backlash_velocity)
        self._monitor_pv(self._dir_pv, self._on_update_direction)

    def _monitor_pv(self, pv, call_back_function):
        """
        Adds a monitor function to a given PV.

        Args:
            pv(String): The pv to monitor
            call_back_function: The function to execute on a pv value change
        """
        if self._ca.pv_exists(pv):
            logger.debug("\nAttempting to monitor {pv_name}".format(pv_name=pv))
            self._ca.add_monitor(pv, call_back_function)
            logger.debug("Monitoring {} for changes.\n".format(pv))

        else:
            logger.error("Error adding monitor to {}: PV does not exist".format(pv))

    def _read_pv(self, pv):
        """
        Read the value from a given PV.

        Args:
            pv(String): The pv to read
        """
        value = self._ca.caget(pv)
        if value is not None:
            return value
        else:
            logger.error("Could not connect to PV {}.".format(pv))
            raise UnableToConnectToPVException(pv, "Check configuration is correct and IOC is running.")

    def _write_pv(self, pv, value):
        """
        Write a value to a given PV.

        Args:
            pv(String): The PV to write to
            value: The new value
        """
        self._ca.caput(pv, value)

    def add_after_rbv_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state

        """
        self._after_rbv_change_listeners.add(listener)

    def add_after_sp_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the read back value of the motor.
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_sp_change_listeners.add(listener)

    def add_after_is_changing_change_listener(self, listener):
        """
        Add a listener which should be called after a change in the dmov (moving) status for a motor
        Args:
            listener: function to call should have two arguments which are the new value and new error state
        """
        self._after_is_changing_change_listeners.add(listener)

    def _trigger_listeners(self, listeners, new_value, alarm_severity, alarm_status):
        for value_change_listener in listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    @property
    def name(self):
        """
        Returns: the name of the underlying PV
        """
        return self._name

    @property
    def resolution(self):
        """
        Returns: The motor resolution for this axis.
        """
        return self._resolution

    @property
    def sp(self):
        """
        Returns: the value of the underlying setpoint PV
        """
        return self._read_pv(self._sp_pv)

    @sp.setter
    def sp(self, value):
        """
        Writes a value to the underlying setpoint PV

        Args:
            value: The value to set
        """
        self._write_pv(self._sp_pv, value)

    @property
    def rbv(self):
        """
        Returns: the value of the underlying readback PV
        """
        return self._read_pv(self._rbv_pv)

    @property
    def velocity(self):
        """
        Returns: the value of the underlying velocity PV
        """
        return self._velocity

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.

        Args:
            value: The value to set
        """
        self._write_pv(self._velo_pv, value)

    @property
    def backlash_distance(self):
        """
        Returns(float): the value of the underlying backlash distance PV
        """
        if self._moving_direction == "Pos":
            return self._backlash_distance * -1.0
        else:
            return self._backlash_distance

    @property
    def backlash_velocity(self):
        """
        Returns: the value of the underlying backlash velocity PV
        """
        return self._backlash_velocity

    @property
    def direction(self):
        """
        Returns: the value of the underlying direction PV
        """
        return self._moving_direction

    def cache_velocity(self):
        """
        Cache the current axis velocity.

        Cache the current axis velocity unless a previously stored cache has not been restored. If the previous cache
        has not been restored then we suspect that a move has been made from outside of the reflectometry server.
        """
        if self._velocity_cache_restored:
            self._velocity_cache = self.velocity
            write_autosave_value(self.name, self._velocity_cache, AutosaveType.VELOCITY)
            self._velocity_cache_restored = False
        elif not self._velocity_cache_restored and self._moving_state == MTR_STOPPED:
            logger.error("Velocity for PV {} has not been cached as existing cache has not been restored and "
                         "is is stationary. Hint: Are you moving the axis outside of the refectory server.".format(self.name))
        elif not self._velocity_cache_restored and self._moving_state == MTR_MOVING:
            # Move interrupting current move. Leave the original cache so it can be restored once all
            # moves have been completed.
            pass

    def restore_cached_velocity(self):
        """
        Restore the cached axis velocity.

        Restore the cached axis velocity from the value stored on the server or, if uninitialised, the autosave file.
        """
        if self._velocity_cache_restored:
            logger.error("Velocity for PV {pv_name} has not been restored from cache. The cache has already been "
                         "restored previously. Hint: Are you moving the axis outside of the refectory server.")
        elif not self._velocity_cache_restored:
            self.velocity = self._velocity_cache
            self._velocity_cache_restored = True

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if new_value == MTR_STOPPED:
            self.restore_cached_velocity()
        self._moving_state = new_value
        self._trigger_listeners(self._after_is_changing_change_listeners, self._dmov_to_bool(new_value),
                                alarm_severity, alarm_status)

    def _dmov_to_bool(self, value):
        """
        Converts the inverted dmov (0=True, 1=False) to the standard format
        """
        return not value

    def _on_update_velocity(self, value, alarm_severity, alarm_status):
        """
        React to an update in the velocity of the underlying motor axis: save value to be restored later if the update
        is not issued by reflectometry server itself.

        Params:
            value (float): The new velocity value
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._velocity = value

    @property
    def is_moving(self):
        """
        Returns: True of the axis is moving
        """
        return self._dmov_to_bool(self._moving_state)

    def _on_update_backlash_distance(self, value, alarm_severity, alarm_status):
        """
        React to an update in the backlash distance of the underlying motor axis.

        Params:
            value (Boolean): The new backlash distance
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._backlash_distance = value

    def _on_update_backlash_velocity(self, value, alarm_severity, alarm_status):
        """
        React to an update in the backlash velocity of the underlying motor axis.

        Params:
            value (Boolean): The new backlash distance
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._backlash_velocity = value

    def _on_update_direction(self, value, alarm_severity, alarm_status):
        """
        React to an update in the direction of the underlying motor axis.

        Params:
            value (Boolean): The new backlash distance
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._moving_direction = value

    def get_distance(self, rbv, set_point_position):
        """
        Args:
            rbv: the read back value
            set_point_position: the set point position
        Returns: The distance between the target component position and the actual motor position in y.
        """
        raise NotImplemented("This should be implemented in the subclass")


class MotorPVWrapper(PVWrapper):
    """
    Wrap a low level motor PV. Provides relevant listeners and synchronization utilities.
    """
    def __init__(self, base_pv, ca=None):
        """
        Creates a wrapper around a low level motor PV.

        Params:
            base_pv (String): The name of the PV
        """
        super(MotorPVWrapper, self).__init__(base_pv, ca)

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis.
        """
        self._sp_pv = self._prefixed_pv
        self._rbv_pv = "{}.RBV".format(self._prefixed_pv)
        self._velo_pv = "{}.VELO".format(self._prefixed_pv)
        self._vmax_pv = "{}.VMAX".format(self._prefixed_pv)
        self._dmov_pv = "{}.DMOV".format(self._prefixed_pv)
        self._bdst_pv = "{}.BDST".format(self._prefixed_pv)
        self._bvel_pv = "{}.BVEL".format(self._prefixed_pv)
        self._dir_pv = "{}.DIR".format(self._prefixed_pv)

    def _set_resolution(self):
        """
        Set the motor resolution for this axis.
        """
        self._resolution = self._read_pv("{}.MRES".format(self._prefixed_pv))


class _JawsAxisPVWrapper(PVWrapper):
    def __init__(self, base_pv, is_vertical, ca=None):
        """
        Creates a wrapper around a jaws axis.

        Params:
            base_pv (String): The name of the PV
            is_vertical (Boolean): Whether the jaws axis moves in the horizontal or vertical direction.
        """
        self.is_vertical = is_vertical
        self._individual_moving_states = {}

        self._directions = []
        self._set_directions()
        self._velocities = {}

        super(_JawsAxisPVWrapper, self).__init__(base_pv, ca)

    def _set_directions(self):
        """
        Set the direction keys used in PVs for this jaws axis.
        """
        if self.is_vertical:
            self._directions = ["JN", "JS"]
            self._direction_symbol = "V"
        else:
            self._directions = ["JE", "JW"]
            self._direction_symbol = "H"

    def _set_resolution(self):
        """
        Set the motor resolution for this axis.
        """
        motor_resolutions_pvs = self._pv_names_for_directions("MTR.MRES")
        motor_resolutions = [self._read_pv(motor_resolutions_pv) for motor_resolutions_pv in motor_resolutions_pvs]
        self._resolution = float(sum(motor_resolutions)) / len(motor_resolutions_pvs)

    def initialise(self):
        """
        Initialise PVWrapper values once the beamline is ready.
        """
        self._init_velocity_cache()
        self._add_monitors()
        for velo_pv in self._pv_names_for_directions("MTR.VELO"):
            self._velocities[self._strip_source_pv(velo_pv)] = self._read_pv(velo_pv)
        self._d_back = 0  # No backlash used as source of clash conditions on jaws sets

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv, partial(self._trigger_listeners, self._after_rbv_change_listeners))
        self._monitor_pv(self._sp_pv, partial(self._trigger_listeners, self._after_sp_change_listeners))
        self._monitor_pv(self._dmov_pv, partial(self._on_update_moving_state))

        for velo_pv in self._pv_names_for_directions("MTR.VELO"):
            self._monitor_pv(velo_pv, partial(self._on_update_individual_velocity,
                                              source=self._strip_source_pv(velo_pv)))

    @property
    def velocity(self):
        """
        Returns: the value of the underlying velocity PV. We use the minimum between the two jaw blades to
        ensure we do not create crash conditions (i.e. one jaw blade going faster than the other one can).
        """
        motor_velocities = self._velocities.values()
        return min([motor_velocities])

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.

        Args:
            value: The value to set
        """
        motor_velocities = self._pv_names_for_directions("MTR.VELO")
        for pv in motor_velocities:
            self._write_pv(pv, value)

    def _set_max_velocity(self):
        """
        Sets the maximum velocity this axis can move at.
        """
        motor_velocities = self._pv_names_for_directions("MTR.VMAX")
        self.max_velocity = min([self._read_pv(pv) for pv in motor_velocities])

    def _pv_names_for_directions(self, suffix):
        """
        Args:
            suffix: pv to read

        Returns: list of pv names for the different directions
        """
        return ["{}:{}:{}".format(self._prefixed_pv, direction, suffix)
                for direction in self._directions]

    def _on_update_individual_velocity(self, value, alarm_severity, alarm_status, source=None):
        self._velocities[source] = value

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status, source=None):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if new_value == MTR_STOPPED:
            self.restore_cached_velocity()
        self._moving_state = new_value
        self._trigger_listeners(self._after_is_changing_change_listeners, self._dmov_to_bool(new_value),
                                alarm_severity, alarm_status)

    def _strip_source_pv(self, pv):
        """
        Extracts the direction key from a given pv.

        Params:
            pv (String): The source pv

        Returns: The direction key embedded within the pv
        """
        for key in self._directions:
            if key in pv:
                return key
        logger.error("Unexpected event source: {}".format(pv))
        logger.error("Unexpected event source: {}".format(pv))


class JawsGapPVWrapper(_JawsAxisPVWrapper):
    """
    Wrap the axis PVs on top of a motor record to allow easy access to all axis PV values needed.
    """
    def __init__(self, base_pv, is_vertical, ca=None):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        Args:
            base_pv (String): The name of the base PV
        """
        super(JawsGapPVWrapper, self).__init__(base_pv, is_vertical, ca)
        self._name = "{}:{}GAP".format(self._name, self._direction_symbol)

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis.
        """
        self._sp_pv = "{}:{}GAP:SP".format(self._prefixed_pv, self._direction_symbol)
        self._rbv_pv = "{}:{}GAP".format(self._prefixed_pv, self._direction_symbol)
        self._dmov_pv = "{}:{}GAP:DMOV".format(self._prefixed_pv, self._direction_symbol)


class JawsCentrePVWrapper(_JawsAxisPVWrapper):
    """
    Wrap the vertical jaws PVs to allow easy access to all motor PV values needed, to allow the centre to track a
    height.
    """

    def __init__(self, base_pv, is_vertical, ca=None):
        """
        Creates a wrapper around a motor PV for accessing its fields.

        Params:
            pv_name (String): The name of the PV
        """
        super(JawsCentrePVWrapper, self).__init__(base_pv, is_vertical, ca)
        self._name = "{}:{}CENT".format(self._name, self._direction_symbol)

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis.
        """
        self._sp_pv = "{}:{}CENT:SP".format(self._prefixed_pv, self._direction_symbol)
        self._rbv_pv = "{}:{}CENT".format(self._prefixed_pv, self._direction_symbol)
        self._dmov_pv = "{}:{}CENT:DMOV".format(self._prefixed_pv, self._direction_symbol)
