"""
Wrapper for motor PVs
"""
from enum import Enum
from functools import partial
from threading import Event

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
        self._prefixed_pv = "{}{}".format(MYPVPREFIX, base_pv)
        self._after_rbv_change_listeners = set()
        self._after_sp_change_listeners = set()
        self._after_dmov_change_listeners = set()

        self._move_initiated = False
        self._moving_state = None
        self._v_restore = None
        self.max_velocity = None
        self._state_init_event = Event()
        self._velocity_event = Event()

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

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv,
                         partial(self._trigger_listeners, "readback value", self._after_rbv_change_listeners))
        self._monitor_pv(self._sp_pv,
                         partial(self._trigger_listeners, "setpoint value", self._after_sp_change_listeners))
        self._monitor_pv(self._dmov_pv,
                         partial(self._trigger_listeners, "moving state value", self._after_dmov_change_listeners))

        self._monitor_pv(self._dmov_pv, self._on_update_moving_state)
        self._monitor_pv(self._velo_pv, self._on_update_velocity)

    def _monitor_pv(self, pv, call_back_function):
        """
        Adds a monitor function to a given PV.

        Args:
            pv(String): The pv to monitor
            call_back_function: The function to execute on a pv value change
        """
        if self._ca.pv_exists(pv):
            self._ca.add_monitor(pv, call_back_function)
            logger.debug("Monitoring {} for changes.".format(pv))
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

    def _trigger_listeners(self, change_type, listeners, new_value, alarm_severity, alarm_status):
        for value_change_listener in listeners:
            value_change_listener(new_value, alarm_severity, alarm_status)

    @property
    def name(self):
        """
        Returns: the name of the underlying PV
        """
        return self._prefixed_pv

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
        return self._read_pv(self._velo_pv)

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.

        Args:
            value: The value to set
        """
        self._write_pv(self._velo_pv, value)

    def initiate_move(self):
        """
        Sets internal state of the pv wrapper to reflect that a move has just been initialised.
        """
        self._move_initiated = True
        self._velocity_event.clear()
        if self._moving_state == MTR_STOPPED:
            self._v_restore = self.velocity
            write_autosave_value(self.name, self._v_restore, AutosaveType.VELOCITY)

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if new_value == MTR_STOPPED and self._v_restore is not None:
            self.velocity = self._v_restore
        if new_value == MTR_MOVING:
            if self._move_initiated:
                self._velocity_event.wait()
                self._move_initiated = False
                self._velocity_event.clear()
        self._moving_state = new_value
        self._state_init_event.set()

    def _on_update_velocity(self, value, alarm_severity, alarm_status):
        """
        React to an update in the velocity of the underlying motor axis: save value to be restored later if the update
        is not issued by reflectometry server itself.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if self._v_restore is None:
            self._init_velocity_to_restore(value)
        elif not self._move_initiated:
            self._v_restore = value
            write_autosave_value(self.name, value, AutosaveType.VELOCITY)
        self._velocity_event.set()

    def _init_velocity_to_restore(self, value):
        """
        Reads the velocity this axis should restore after a beamline move ends. Initialises to the current value unless
        the motor is currently moving and an autosave value can be read.
        """
        v_init = value
        v_autosaved = read_autosave_value(self.name, AutosaveType.VELOCITY)
        self._state_init_event.wait()
        if self._moving_state == MTR_MOVING:
            if v_autosaved is not None:
                v_init = v_autosaved
        self._v_restore = v_init
        write_autosave_value(self.name, v_init, AutosaveType.VELOCITY)


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
        self._state_init_event = Event()

        self._directions = []
        self._set_directions()

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
        self._add_monitors()
        self._init_velocity_to_restore(self.velocity)

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv,
                         partial(self._trigger_listeners, "readback value", self._after_rbv_change_listeners))
        self._monitor_pv(self._sp_pv,
                         partial(self._trigger_listeners, "setpoint value", self._after_sp_change_listeners))
        self._monitor_pv(self._dmov_pv,
                         partial(self._on_update_moving_state, "moving state value"))

    @property
    def velocity(self):
        """
        Returns: the value of the underlying velocity PV. We use the minimum between the two jaw blades to
        ensure we do not create crash conditions (i.e. one jaw blade going faster than the other one can).
        """
        motor_velocities = self._pv_names_for_directions("MTR.VELO")
        return min([self._read_pv(pv) for pv in motor_velocities])

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

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status, source=None):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if new_value == MTR_STOPPED and self._v_restore is not None:
            self.velocity = self._v_restore
        self._moving_state = new_value
        self._state_init_event.set()

    def _init_velocity_to_restore(self, value):
        """
        Reads the velocity this axis should restore after a beamline move ends. Initialises to the given value unless
        the motor is currently moving and an autosave value can be read.
        """
        v_init = value
        v_autosaved = read_autosave_value(self.name, AutosaveType.VELOCITY)
        self._state_init_event.wait()
        if self._moving_state == MTR_MOVING:
            if v_autosaved is not None:
                v_init = v_autosaved
        self._v_restore = v_init
        write_autosave_value(self.name, v_init, AutosaveType.VELOCITY)

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

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis.
        """
        self._sp_pv = "{}:{}CENT:SP".format(self._prefixed_pv, self._direction_symbol)
        self._rbv_pv = "{}:{}CENT".format(self._prefixed_pv, self._direction_symbol)
        self._dmov_pv = "{}:{}CENT:DMOV".format(self._prefixed_pv, self._direction_symbol)
