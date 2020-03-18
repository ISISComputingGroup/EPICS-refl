"""
Wrapper for motor PVs
"""
import abc
import threading
from collections import namedtuple
import time
from functools import partial

import six
from contextlib2 import contextmanager

from ReflectometryServer.ChannelAccess.constants import MYPVPREFIX, MTR_MOVING, MTR_STOPPED
from ReflectometryServer.file_io import velocity_float_autosave, velocity_bool_autosave, param_bool_autosave
import logging

from server_common.channel_access import ChannelAccess, UnableToConnectToPVException
from server_common.observable import observable

# Time between monitor update processing to allow for multiple monitors to be collected together providing a single
# update trigger
MIN_TIME_BETWEEN_MONITOR_UPDATES_FROM_MONITORS = 0.05

logger = logging.getLogger(__name__)
RETRY_INTERVAL = 5

DEFAULT_SCALE_FACTOR = 100.0


# An update of the setpoint value of this motor axis.
SetpointUpdate = namedtuple("SetpointUpdate", [
    "value",            # The new setpoint value of the axis (float)
    "alarm_severity",   # The alarm severity of the axis, represented as an integer (see Channel Access doc)
    "alarm_status"])    # The alarm status of the axis, represented as an integer (see Channel Access doc)

# An update of the readback value of this motor axis.
ReadbackUpdate = namedtuple("ReadbackUpdate", [
    "value",            # The new readback value of the axis (float)
    "alarm_severity",   # The alarm severity of the axis, represented as an integer (see Channel Access doc)
    "alarm_status"])    # The alarm status of the axis, represented as an integer (see Channel Access doc)

# An update of the is-changing state of this motor axis.
IsChangingUpdate = namedtuple("IsChangingUpdate", [
    "value",            # The new is-changing state of the axis (boolean)
    "alarm_severity",   # The alarm severity of the axis, represented as an integer (see Channel Access doc)
    "alarm_status"])    # The alarm status of the axis, represented as an integer (see Channel Access doc)


class ProcessMonitorEvents(object):
    """
    Collect updates produced and only apply the latest ones.
    """

    def __init__(self):
        self.triggers_lock = threading.RLock()
        self.triggers = {}
        self._process_triggers = threading.Event()
        self._process_triggers.clear()

    def add_trigger(self, trigger_fn, update, start_processing=True):
        """
        Add a trigger to be called. These are stored by update type so that future updates can overwrite previous
        updates
        Args:
            trigger_fn: function to trigger
            update: update to pass to that trigger
            start_processing: True to start the processing loop; False don't process until loop is started
        """
        with self.triggers_lock:
            self.triggers[(trigger_fn, update.__class__)] = (trigger_fn, update)
            if start_processing and not self._process_triggers.is_set():
                self._process_triggers.set()
                threading.Thread(target=self.process_triggers_loop).start()

    def process_triggers_loop(self):
        """
        Process triggers on the list while process triggers is True
        """
        while True:
            try:
                self.process_current_triggers()
                if self._process_triggers.is_set():
                    time.sleep(MIN_TIME_BETWEEN_MONITOR_UPDATES_FROM_MONITORS)
                else:
                    break
            except Exception as e:
                logger.error("Exception occurred in process events: {}".format(e))

    def process_current_triggers(self):
        """
        Process the current event set clearing the process triggers if the list becomes empty.
        """
        with self.triggers_lock:
            events_to_process = self.triggers
            self.triggers = {}

            # if there are no triggers then clear the process triggers flag. If an event comes in after this a new
            #  thread will be started to process those events
            if len(events_to_process) == 0:
                self._process_triggers.clear()

        for listener_trigger_fn, event in events_to_process.values():
            try:
                listener_trigger_fn(event)
            except Exception as e:
                logger.error("Exception occurred in processing an event: {}".format(e))


# Process triggers that derive from PV Monitors
PROCESS_MONITOR_EVENTS = ProcessMonitorEvents()


@six.add_metaclass(abc.ABCMeta)
@observable(SetpointUpdate, ReadbackUpdate, IsChangingUpdate)
class PVWrapper(object):
    """
    Wrap a single motor axis. Provides relevant listeners and synchronization utilities.
    """
    def __init__(self, base_pv, ca=None, min_velocity_scale_factor=None):
        """
        Creates a wrapper around a PV.

        Args:
            base_pv(String): The name of the PV
            ca: The Channel Access server to use
            min_velocity_scale_factor: The factor by which to scale down vmax to use as minimum velocity.
        """
        if ca is None:
            self._ca = ChannelAccess
        else:
            self._ca = ca
        self._name = base_pv
        self._prefixed_pv = "{}{}".format(MYPVPREFIX, base_pv)

        if min_velocity_scale_factor is None:
            self._min_velocity_scale_factor = DEFAULT_SCALE_FACTOR
        elif min_velocity_scale_factor <= 0:
            logger.error("Minimum velocity scale level {} is invalid (Should be > 0). "
                         "Setting default scaling factor of 100".format(min_velocity_scale_factor))
            self._min_velocity_scale_factor = DEFAULT_SCALE_FACTOR
        else:
            self._min_velocity_scale_factor = min_velocity_scale_factor

        self._moving_state_cache = None
        self._moving_direction_cache = None
        self._velocity_restored = None
        self._velocity_to_restore = None
        self._velocity_cache = None
        self._backlash_distance_cache = None
        self._backlash_velocity_cache = None
        self._max_velocity_cache = None
        self._base_velocity_cache = None
        self._resolution = None

        self._set_pvs()

        self._block_until_pv_available()

    def _block_until_pv_available(self):
        """
        Blocks the process until the PV this driver is pointing at is available.
        """
        while not self._ca.pv_exists(self._rbv_pv):
            logger.error(
                "{} does not exist. Check the PV is correct and the IOC is running. Retrying in {} s.".format(
                    self._rbv_pv, RETRY_INTERVAL))
            time.sleep(RETRY_INTERVAL)

    @abc.abstractmethod
    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis. Must be overridden in subclass.
        """

    @abc.abstractmethod
    def _set_resolution(self):
        """
        Set the motor resolution for this axis. Must be overridden in subclass.
        """
        raise NotImplementedError()

    def initialise(self):
        """
        Initialise PVWrapper values once the beamline is ready.
        """
        self._set_resolution()
        self._add_monitors()
        self._velocity_cache = self._read_pv(self._velo_pv)
        self._backlash_distance_cache = self._read_pv(self._bdst_pv)
        self._backlash_velocity_cache = self._read_pv(self._bvel_pv)
        self._moving_direction_cache = self._read_pv(self._dir_pv)
        self._max_velocity_cache = self._read_pv(self._vmax_pv)
        self._base_velocity_cache = self._read_pv(self._vbas_pv)
        self._init_velocity_cache()

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv, self._on_update_readback_value)
        self._monitor_pv(self._sp_pv, self._on_update_setpoint_value)
        self._monitor_pv(self._dmov_pv, self._on_update_moving_state)
        self._monitor_pv(self._velo_pv, self._on_update_velocity)
        self._monitor_pv(self._bdst_pv, self._on_update_backlash_distance)
        self._monitor_pv(self._bvel_pv, self._on_update_backlash_velocity)
        self._monitor_pv(self._dir_pv, self._on_update_direction)

    def _monitor_pv(self, pv, call_back_function):
        """
        Adds a monitor function to a given PV.

        Args:
            pv (String): The pv to monitor
            call_back_function: The function to execute on a pv value change
        """
        while True:
            if self._ca.pv_exists(pv):
                self._ca.add_monitor(pv, call_back_function)
                logger.debug("Monitoring {} for changes.".format(pv))
                break
            else:
                logger.error(
                    "Error adding monitor to {}: PV does not exist. Check the PV is correct and the IOC is running. "
                    "Retrying in {} s.".format(pv, RETRY_INTERVAL))
                time.sleep(RETRY_INTERVAL)

    def _read_pv(self, pv):
        """
        Read the value from a given PV.

        Args:
            pv (String): The pv to read
        """
        value = self._ca.caget(pv)
        if value is not None:
            return value
        else:
            logger.error("Could not connect to PV {}.".format(pv))
            raise UnableToConnectToPVException(pv, "Check configuration is correct and IOC is running.")

    def _write_pv(self, pv, value, wait=False):
        """
        Write a value to a given PV.

        Args:
            pv (String): The PV to write to
            value: The new value
            wait: wait for call back
        """
        self._ca.caput(pv, value, wait=wait)

    @property
    def name(self):
        """
        Returns (String): the name of the underlying PV
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
        logger.info("{}: Moving axis to new position: {}".format(self.name, value))
        self._write_pv(self._sp_pv, value)

    @property
    def rbv(self):
        """
        Returns (float): the value of the underlying readback PV
        """
        return self._read_pv(self._rbv_pv)

    @property
    def velocity(self):
        """
        Returns (float): the value of the underlying velocity PV
        """
        return self._velocity_cache

    @velocity.setter
    def velocity(self, value):
        """
        Writes a value to the underlying velocity PV's VAL field.

        Args:
            value (float): The value to set
        """
        self._write_pv(self._velo_pv, value)

    @property
    def max_velocity(self):
        """
        Returns (float): The maximum velocity for the axis
        """
        return self._max_velocity_cache

    @property
    def min_velocity(self):
        """
        Returns (float): the minimum velocity at which this axis is allowed to move to prevent stalling.
        """
        if self._base_velocity_cache:
            return self._base_velocity_cache
        else:
            return self._max_velocity_cache / self._min_velocity_scale_factor

    @property
    def backlash_distance(self):
        """
        Returns(float): the value of the underlying backlash distance PV
        """
        if self._moving_direction_cache == "Pos":
            return self._backlash_distance_cache * -1.0
        else:
            return self._backlash_distance_cache

    @property
    def backlash_velocity(self):
        """
        Returns (float): the value of the underlying backlash velocity PV
        """
        return self._backlash_velocity_cache

    @property
    def direction(self):
        """
        Returns: the value of the underlying direction PV
        """
        return self._moving_direction_cache

    def _init_velocity_cache(self):
        """
        Initialise the velocity cache for the current axis.

        Initialise the velocity cache and its restored status. If no cache exists then load the last velocity value
        from the auto-save file.
        """
        autosave_value = velocity_float_autosave.read_parameter(self.name, None)
        if autosave_value is not None:
            logger.debug("Restoring {pv_name} velocity_cache with auto-save value {value}"
                         .format(pv_name=self.name, value=autosave_value))
            self._velocity_to_restore = autosave_value
        else:
            logger.error("Error: Unable to initialise velocity cache from auto-save for {}."
                         .format(self.name))

        if autosave_value is not None:
            autosave_value = velocity_bool_autosave.read_parameter(self.name + "_velocity_restored", None)
            if autosave_value is not None:
                logger.debug("Restoring {pv_name} velocity_cache_restored with auto-save value {value}"
                             .format(pv_name=self.name, value=autosave_value))
                self._velocity_restored = autosave_value
            else:
                logger.error("Error: Unable to initialise velocity cache (restored flag) from auto-save for {}."
                             .format(self.name))

    def cache_velocity(self):
        """
        Cache the current axis velocity.

        Cache the current axis velocity unless a previously stored cache has not been restored. If the previous cache
        has not been restored then we suspect that a move has been made from outside of the reflectometry server.
        """
        if self._velocity_restored:
            self._velocity_to_restore = self.velocity
            velocity_float_autosave.write_parameter(self.name, self._velocity_to_restore)
            self._velocity_restored = False
            velocity_bool_autosave.write_parameter(self.name + "_velocity_restored", self._velocity_restored)
        elif not self._velocity_restored and self._moving_state_cache == MTR_STOPPED:
            logger.error("Velocity for {pv_name} has not been cached as existing cache has not been restored and "
                         "is stationary."
                         .format(pv_name=self.name))
        elif not self._velocity_restored and self._moving_state_cache == MTR_MOVING:
            # Move interrupting current move. Leave the original cache so it can be restored once all
            # moves have been completed.
            pass

    def restore_pre_move_velocity(self):
        """
        Restore the cached axis velocity.

        Restore the cached axis velocity from the value stored on the server and update the restored cache status.
        """
        if self._velocity_restored:
            logger.error("Velocity for PV {pv_name} has not been restored from cache. The cache has already been "
                         "restored previously. Hint: Are you moving the axis outside of the reflectometry server?"
                         .format(pv_name=self.name))
        else:
            if self._velocity_to_restore is None:
                logger.error("Cannot restore velocity: velocity cache is None for {pv_name}".format(pv_name=self.name))
            else:
                logger.debug("Restoring velocity cache of {value} for PV {pv_name}"
                             .format(value=self._velocity_to_restore, pv_name=self.name))
                self._write_pv(self._velo_pv, self._velocity_to_restore)
            self._velocity_restored = True
            param_bool_autosave.write_parameter(self.name + "_velocity_restored", self._velocity_restored)

    def _on_update_setpoint_value(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the setpoint value of the underlying motor axis.

        Params:
            value (Boolean): The new setpoint value
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        PROCESS_MONITOR_EVENTS.add_trigger(self.trigger_listeners,
                                           SetpointUpdate(new_value, alarm_severity, alarm_status))

    def _on_update_readback_value(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the readback value of the underlying motor axis.

        Params:
            value (Boolean): The new readback value
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """

        PROCESS_MONITOR_EVENTS.add_trigger(self.trigger_listeners,
                                           ReadbackUpdate(new_value, alarm_severity, alarm_status))

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        if new_value == MTR_STOPPED:
            self.restore_pre_move_velocity()
        self._moving_state_cache = new_value

        changing_update = IsChangingUpdate(self._dmov_to_bool(new_value), alarm_severity, alarm_status)
        PROCESS_MONITOR_EVENTS.add_trigger(self.trigger_listeners, changing_update)

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
        self._velocity_cache = value

    @property
    def is_moving(self):
        """
        Returns (Bool): True of the axis is moving
        """
        return self._dmov_to_bool(self._moving_state_cache)

    def _on_update_backlash_distance(self, value, alarm_severity, alarm_status):
        """
        React to an update in the backlash distance of the underlying motor axis.

        Params:
            value (float): The new backlash distance
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._backlash_distance_cache = value

    def _on_update_backlash_velocity(self, value, alarm_severity, alarm_status):
        """
        React to an update in the backlash velocity of the underlying motor axis.

        Params:
            value (float): The new backlash velocity
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._backlash_velocity_cache = value

    def _on_update_direction(self, value, alarm_severity, alarm_status):
        """
        React to an update in the direction of the underlying motor axis.

        Params:
            value (String): The new backlash distance
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._moving_direction_cache = value

    @abc.abstractmethod
    def define_position_as(self, new_position):
        """
        Set the current position in the underlying hardware as the new position without moving anything
        Args:
            new_position: position to move to
        """

    @contextmanager
    def _motor_in_set_mode(self, motor_pv):
        """
        Uses a context to place motor into set mode and ensure that it leaves set mode after context has ended. If it
        can not set the mode correctly will not run the yield.
        Args:
            motor_pv: motor pv on which to set the mode

        Returns:
        """

        calibration_set_pv = "{}.SET".format(motor_pv)
        offset_freeze_switch_pv = "{}.FOFF".format(motor_pv)

        try:
            self._ca.caput_retry_on_fail(calibration_set_pv, "Set")
            offset_freeze_switch = self._read_pv(offset_freeze_switch_pv)
            self._ca.caput_retry_on_fail(offset_freeze_switch_pv, "Frozen")
        except IOError as ex:
            raise ValueError("Can not set motor set and frozen offset mode: {}".format(ex))

        try:
            yield
        finally:
            try:
                self._ca.caput_retry_on_fail(calibration_set_pv, "Use")
                self._ca.caput_retry_on_fail(offset_freeze_switch_pv, offset_freeze_switch)
            except IOError as ex:
                raise ValueError("Can not reset motor set and frozen offset mode: {}".format(ex))


class MotorPVWrapper(PVWrapper):
    """
    Wrap a low level motor PV. Provides relevant listeners and synchronization utilities.
    """
    def __init__(self, base_pv, ca=None, min_velocity_scale_factor=None):
        """
        Creates a wrapper around a low level motor PV.

        Params:
            base_pv (String): The name of the PV
            ca: The Channel Access server to use
            min_velocity_scale_factor: The factor by which to scale down vmax to use as minimum velocity.
        """
        super(MotorPVWrapper, self).__init__(base_pv, ca, min_velocity_scale_factor)

    def _set_pvs(self):
        """
        Define relevant PVs for this type of axis.
        """
        self._sp_pv = self._prefixed_pv
        self._rbv_pv = "{}.RBV".format(self._prefixed_pv)
        self._velo_pv = "{}.VELO".format(self._prefixed_pv)
        self._vmax_pv = "{}.VMAX".format(self._prefixed_pv)
        self._vbas_pv = "{}.VBAS".format(self._prefixed_pv)
        self._dmov_pv = "{}.DMOV".format(self._prefixed_pv)
        self._bdst_pv = "{}.BDST".format(self._prefixed_pv)
        self._bvel_pv = "{}.BVEL".format(self._prefixed_pv)
        self._dir_pv = "{}.DIR".format(self._prefixed_pv)

    def _set_resolution(self):
        """
        Set the motor resolution for this axis.
        """
        self._resolution = self._read_pv("{}.MRES".format(self._prefixed_pv))

    def define_position_as(self, new_position):
        """
        Set the current position in the underlying hardware as the new position without moving anything
        Args:
            new_position: position to move to
        """
        try:
            with self._motor_in_set_mode(self._prefixed_pv):
                self._write_pv(self._sp_pv, new_position)
        except ValueError as ex:
            logger.error("Can not define zero: {}".format(ex))


@six.add_metaclass(abc.ABCMeta)
class _JawsAxisPVWrapper(PVWrapper):
    def __init__(self, base_pv, is_vertical, ca=None):
        """
        Creates a wrapper around a jaws axis.

        Params:
            base_pv (String): The name of the PV
            is_vertical (Boolean): False for horizontal jaws, true for vertical jaws
            ca: The Channel Access server to use
        """
        self.is_vertical = is_vertical

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
        self._add_monitors()
        for velo_pv in self._pv_names_for_directions("MTR.VELO"):
            self._velocities[self._strip_source_pv(velo_pv)] = self._read_pv(velo_pv)

        motor_max_velocities = self._pv_names_for_directions("MTR.VMAX")
        self._max_velocity_cache = min([self._read_pv(pv) for pv in motor_max_velocities])

        motor_base_velocities = self._pv_names_for_directions("MTR.VBAS")
        self._base_velocity_cache = max([self._read_pv(pv) for pv in motor_base_velocities])

        self._backlash_distance_cache = 0  # No backlash used as source of clash conditions on jaws sets

    def _add_monitors(self):
        """
        Add monitors to the relevant motor PVs.
        """
        self._monitor_pv(self._rbv_pv, self._on_update_readback_value)
        self._monitor_pv(self._sp_pv, self._on_update_setpoint_value)
        self._monitor_pv(self._dmov_pv, self._on_update_moving_state)

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
            value (float): The value to set
        """
        logger.error("Error: An attempt was made to write a velocity to a Jaws Axis. We do not support this "
                     "as we do not expect jaws to be synchronised.")

    @property
    def max_velocity(self):
        """
        Sets the maximum velocity this axis can move at.
        """
        return self._max_velocity_cache

    def _pv_names_for_directions(self, suffix):
        """
        Args:
            suffix (String): pv to read

        Returns (String): list of pv names for the different directions
        """
        return ["{}:{}:{}".format(self._prefixed_pv, direction, suffix)
                for direction in self._directions]

    def _on_update_individual_velocity(self, value, alarm_severity, alarm_status, source=None):
        self._velocities[source] = value

    def _on_update_moving_state(self, new_value, alarm_severity, alarm_status):
        """
        React to an update in the motion status of the underlying motor axis.

        Params:
            value (Boolean): The new motion status
            alarm_severity (server_common.channel_access.AlarmSeverity): severity of any alarm
            alarm_status (server_common.channel_access.AlarmCondition): the alarm status
        """
        self._moving_state_cache = new_value
        changing_update = IsChangingUpdate(self._dmov_to_bool(new_value), alarm_severity, alarm_status)
        PROCESS_MONITOR_EVENTS.add_trigger(self.trigger_listeners, changing_update)

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

    def define_position_as(self, new_position):
        """
        Set the current position in the underlying hardware as the new position without moving anything
        Args:
            new_position: position to move to
        """
        try:
            mtr1, mtr2 = self._pv_names_for_directions("MTR")
            logger.info("Defining position for axis {name} to {corrected_value}. "
                        "From sp {sp} and rbv {rbv}.".format(name=self.name, corrected_value=new_position,
                                                             sp=self.sp, rbv=self.rbv))
            for motor in self._pv_names_for_directions("MTR"):
                rbv = self._read_pv("{}.RBV".format(motor))
                sp = self._read_pv("{}".format(motor))
                logger.info("    Motor {name} initially at rbv {rbv} sp {sp}".format(name=motor, rbv=rbv, sp=sp))

            with self._motor_in_set_mode(mtr1), self._motor_in_set_mode(mtr2):
                    self._write_pv(self._sp_pv, new_position)

            for motor in self._pv_names_for_directions("MTR"):
                rbv = self._read_pv("{}.RBV".format(motor))
                sp = self._read_pv("{}".format(motor))
                logger.info("    Motor {name} moved to rbv {rbv} sp {sp}".format(name=motor, rbv=rbv, sp=sp))
        except ValueError as ex:
            logger.error("Can not define zero: {}".format(ex))


class JawsGapPVWrapper(_JawsAxisPVWrapper):
    """
    Wrap the axis PVs on top of a motor record to allow easy access to all axis PV values needed.
    """
    def __init__(self, base_pv, is_vertical, ca=None):
        """
        Creates a wrapper around a motor PV for accessing its fields.
        Args:
            base_pv (String): The name of the base PV
            is_vertical (Boolean): False for horizontal jaws, true for vertical jaws
            ca: The Channel Access server to use
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
            is_vertical (Boolean): False for horizontal jaws, true for vertical jaws
            ca: The Channel Access server to use
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
