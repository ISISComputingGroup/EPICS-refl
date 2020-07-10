"""
The driving layer communicates between the component layer and underlying pvs.
"""
import math
import logging
from collections import namedtuple

from pcaspy import Severity

from ReflectometryServer.out_of_beam import OutOfBeamLookup
from ReflectometryServer.engineering_corrections import NoCorrection, CorrectionUpdate
from ReflectometryServer.axis import DefineValueAsEvent
from ReflectometryServer import ChangeAxis
from ReflectometryServer.pv_wrapper import SetpointUpdate, ReadbackUpdate, IsChangingUpdate
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo
from server_common.observable import observable


logger = logging.getLogger(__name__)

# Event that is triggered when a new readback value is read from the axis (with corrections applied)
CorrectedReadbackUpdate = namedtuple("CorrectedReadbackUpdate", [
    "value",            # The new (corrected) readback value of the axis (float)
    "alarm_severity",   # The alarm severity of the axis, represented as an integer (see Channel Access doc)
    "alarm_status"])    # The alarm status of the axis, represented as an integer (see Channel Access doc)


@observable(CorrectionUpdate, CorrectedReadbackUpdate)
class IocDriver:
    """
    Drives an actual motor axis based on a component in the beamline model.
    """
    def __init__(self, component, component_axis, motor_axis, out_of_beam_positions=None, synchronised=True,
                 engineering_correction=None):
        """
        Drive the IOC based on a component
        Args:
            component (ReflectometryServer.components.Component): Component for IOC driver
            motor_axis (ReflectometryServer.pv_wrapper.PVWrapper): The PV that this driver controls.
            out_of_beam_positions (ReflectometryServer.out_of_beam_lookup.OutOfBeamLookup): Provides the out of beam
                status as configured for this motor_axis.
            synchronised (bool): If True then axes will set their velocities so they arrive at the end point at the same
                time; if false they will move at their current speed.
            engineering_correction (ReflectometryServer.engineering_corrections.EngineeringCorrection): the engineering
                correction to apply to the value from the component before it is sent to the pv. None for no correction
        """
        self._component = component
        self._component_axis = component_axis
        self._motor_axis = motor_axis
        self.name = motor_axis.name
        if out_of_beam_positions is None or not component_axis == ChangeAxis.POSITION:  # TODO: sort in park position ticket
            self._out_of_beam_lookup = None
        else:
            try:
                self._out_of_beam_lookup = OutOfBeamLookup(out_of_beam_positions)
            except ValueError as e:
                STATUS_MANAGER.update_error_log(str(e))
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Invalid Out Of Beam Positions", self.name, Severity.MINOR_ALARM))

        self._synchronised = synchronised
        if engineering_correction is None:
            self._engineering_correction = NoCorrection()
            self.has_engineering_correction = False
        else:
            self.has_engineering_correction = True
            self._engineering_correction = engineering_correction
            self._engineering_correction.add_listener(CorrectionUpdate, self._on_correction_update)

        self._sp_cache = None
        self._rbv_cache = self._engineering_correction.from_axis(self._motor_axis.rbv, self._get_component_sp())

        self._motor_axis.add_listener(SetpointUpdate, self._on_update_sp)
        self._motor_axis.add_listener(ReadbackUpdate, self._on_update_rbv)
        self._motor_axis.add_listener(IsChangingUpdate, self._on_update_is_changing)
        self._component.beam_path_rbv.axis[component_axis].add_listener(DefineValueAsEvent, self._on_define_value_as)

    def _on_define_value_as(self, new_event):
        """
        When a define value as occurs then set the value on the axis

        Args:
            new_event (DefineValueAsEvent): The events value and axis

        """
        correct_position = self._engineering_correction.to_axis(new_event.new_position)
        logger.info("Defining position for axis {name} to {corrected_value} (uncorrected {new_value}). "
                    "From sp {sp} and rbv {rbv}".format(name=self._motor_axis.name, corrected_value=correct_position,
                                                        new_value=new_event.new_position, sp=self._sp_cache,
                                                        rbv=self._rbv_cache))
        self._motor_axis.define_position_as(correct_position)

    def _on_correction_update(self, new_correction_value):
        """

        Args:
            new_correction_value (CorrectionUpdate): the new correction value

        """
        description = "{} on {} for {}".format(new_correction_value.description, self.name, self._component.name)
        self.trigger_listeners(CorrectionUpdate(new_correction_value.correction, description))

    def __repr__(self):
        return "{} for axis pv {} and component {}".format(
            self.__class__.__name__, self._motor_axis.name, self._component.name)

    def initialise(self):
        """
        Post monitors and read initial value from the axis.
        """
        self._motor_axis.initialise()
        self.initialise_setpoint()

    def initialise_setpoint(self):
        """
        Initialise the setpoint beam model in the component layer with an initial value read from the motor axis.
        """
        beam_path_setpoint = self._component.beam_path_set_point
        autosaved_value = beam_path_setpoint.axis[self._component_axis].autosaved_value
        if autosaved_value is None:
            corrected_axis_setpoint = self._engineering_correction.init_from_axis(self._motor_axis.sp)
        else:
            corrected_axis_setpoint = self._engineering_correction.from_axis(self._motor_axis.sp, autosaved_value)

        if self._out_of_beam_lookup is not None:  # TODO: sort in park position ticket
            beam_interception = beam_path_setpoint.calculate_beam_interception()
            in_beam_status = self._get_in_beam_status(beam_interception, self._motor_axis.sp)
            beam_path_setpoint.is_in_beam = in_beam_status
            # if the motor_axis is out of the beam then no correction needs adding to setpoint
            if not in_beam_status:
                corrected_axis_setpoint = self._motor_axis.sp

        beam_path_setpoint.axis[self._component_axis].init_displacement_from_motor(corrected_axis_setpoint)

    def is_for_component(self, component):
        """
        Does this driver use the component given.
        Args:
            component: the component to check

        Returns: True if this ioc driver uses the component; false otherwise
        """
        return component is self._component

    def _axis_will_move(self):
        """
        Returns: True if the axis set point has changed and it will move any distance
        """
        return not self.at_target_setpoint() and \
            self._component.beam_path_set_point.axis[self._component_axis].is_changed

    def _backlash_duration(self):
        """
        Returns: the duration of the backlash move
        """
        backlash_distance, distance_to_move, is_within_backlash_distance = self._get_movement_distances()
        backlash_velocity = self._motor_axis.backlash_velocity

        if backlash_velocity is None or backlash_distance == 0 or backlash_distance is None:
            # Return 0 instead of error as when this is called by perform_move it can be on motors which are
            # not in fact moving, and may not have been set up yet
            return 0.0
        elif backlash_velocity == 0:
            raise ZeroDivisionError("Backlash speed is zero")

        if is_within_backlash_distance:
            # If the motor is already within the backlash distance
            return math.fabs(distance_to_move) / backlash_velocity
        else:
            return math.fabs(backlash_distance) / backlash_velocity

    def _base_move_duration(self):
        """
        Returns: the duration move without the backlash
        """
        max_velocity = self._motor_axis.max_velocity
        if max_velocity is None:
            return 0.0

        backlash_distance, distance_to_move, is_within_backlash_distance = self._get_movement_distances()
        if is_within_backlash_distance:
            return 0.0
        else:
            # If the motor is not already within the backlash distance
            if max_velocity == 0.0:
                raise ZeroDivisionError("Motor max velocity is zero or none")
            return math.fabs(distance_to_move - backlash_distance) / max_velocity

    def _get_movement_distances(self):
        """
        Returns:
            backlash_distance: backlash distance if set; 0 if not
            distance_to_move: distance that the motor needs to move to be the same as the component set point
            is_within_backlash_distance: True if the distance to move is within the backlash distance
        """
        backlash_distance = self._motor_axis.backlash_distance or 0.0
        distance_to_move = self.rbv_cache() - self._get_component_sp()
        is_within_backlash_distance = min([0.0, backlash_distance]) <= distance_to_move <= max([0.0, backlash_distance])
        return backlash_distance, distance_to_move, is_within_backlash_distance

    def get_max_move_duration(self):
        """
        Returns: The maximum duration of the requested move for all associated axes. If axes are not synchronised this
        will return 0 but movement will still be required.
        """
        duration = 0.0
        if self._axis_will_move() and self._synchronised:
            if self._motor_axis.max_velocity == 0 or self._motor_axis.max_velocity is None:
                raise ZeroDivisionError("Motor max velocity is zero or none")
            backlash_duration = self._backlash_duration()
            base_move_duration = self._base_move_duration()
            duration = base_move_duration + backlash_duration

            logger.debug("Shortest move duration for {}: {:.2f}s ({:.2f}s base; {:.2f}s backlash)"
                         .format(self.name, duration, base_move_duration, backlash_duration))
        return duration

    def perform_move(self, move_duration, force=False):
        """
        Tells the driver to perform a move to the component set points within a given duration.
        The axis will update the set point cache when it is changed so don't need to do it here

        Args:
            move_duration (float): The duration in which to perform this move
            force (bool): move even if component does not report changed
        """
        if self._axis_will_move() or force:
            move_duration -= self._backlash_duration()
            if move_duration > 1e-6 and self._synchronised:
                self._motor_axis.cache_velocity()
                self._motor_axis.velocity = max(self._motor_axis.min_velocity, self._get_distance() / move_duration)
            self._motor_axis.sp = self._engineering_correction.to_axis(self._get_component_sp())

        self._component.beam_path_set_point.axis[self._component_axis].is_changed = False

    def rbv_cache(self):
        """
        Return the last cached readback value of the underlying motor if one exists; throws an exception otherwise.

        Returns: The cached readback value for the motor
        """
        if self._rbv_cache is None:
            raise ValueError("Axis {} not initialised. Check configuration is correct and motor IOC is running."
                             .format(self._motor_axis.name))
        return self._rbv_cache

    def _get_distance(self):
        """
        Returns:
            The distance between the target component position and the actual motor position excluding the backlash.
        """

        backlash_distance = self._motor_axis.backlash_distance
        return math.fabs(self.rbv_cache() - (self._get_component_sp() + backlash_distance))

    def _get_component_sp(self):
        """
        Returns: position that the set point axis is set to
        """
        if self._component.beam_path_set_point.is_in_beam or not self._component_axis == ChangeAxis.POSITION:  # TODO Fix when multiple park postions
            displacement = self._component.beam_path_set_point.axis[self._component_axis].get_displacement()
        else:
            if self._out_of_beam_lookup is None:
                displacement = 0
                STATUS_MANAGER.update_error_log(
                    "The component {} is out of the beam but there is no out of beam position for the driver "
                    "running motor_axis {}".format(self._component.name, self._motor_axis.name))
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("No out of beam position defined for motor_axis", self.name, Severity.MINOR_ALARM))
            else:
                beam_interception = self._component.beam_path_set_point.calculate_beam_interception()
                displacement = self._out_of_beam_lookup.get_position_for_intercept(beam_interception).position
        return displacement

    def _on_update_rbv(self, update):
        """
        Listener to trigger on a change of the readback value of the underlying motor.

        Args:
            update (ReflectometryServer.pv_wrapper.ReadbackUpdate): update of the readback value of the axis
        """
        corrected_new_value = self._engineering_correction.from_axis(update.value, self._get_component_sp())
        self._rbv_cache = corrected_new_value
        self._propagate_rbv_change(
            CorrectedReadbackUpdate(corrected_new_value, update.alarm_severity, update.alarm_status))

    def _propagate_rbv_change(self, update):
        """
        Signal that the motor readback value has changed to the middle component layer. Subclass must implement this
        method.
        """
        if self._component_axis == ChangeAxis.POSITION:  # TODO: sort in park position ticket
            if self._out_of_beam_lookup is not None:
                beam_interception = self._component.beam_path_rbv.calculate_beam_interception()
                self._component.beam_path_rbv.is_in_beam = self._get_in_beam_status(beam_interception, update.value)

        self._component.beam_path_rbv.axis[self._component_axis].set_displacement(update)

    def _get_in_beam_status(self, beam_intersect, value):
        if self._out_of_beam_lookup is not None:
            in_beam_status = self._out_of_beam_lookup.is_in_beam(beam_intersect, value)
        else:
            in_beam_status = True
        return in_beam_status

    def _on_update_sp(self, update):
        """
        Updates the cached set point from the axis with a new value.

        Args:
            update (ReflectometryServer.pv_wrapper.SetpointUpdate): update of the setpoint value of the axis
        """
        self._sp_cache = self._engineering_correction.from_axis(update.value, self._get_component_sp())

    def _on_update_is_changing(self, update):
        """
        Updates the cached is_moving field for the motor record with a new value if the underlying motor rbv is changing

        Args:
            update (ReflectometryServer.pv_wrapper.IsChangingUpdate): update of the is_moving status of the axis
        """
        self._component.beam_path_rbv.axis[self._component_axis].is_changing = update.value

    def at_target_setpoint(self):
        """
        Returns: True if the setpoint on the component and the one on the motor PV are the same (within tolerance),
            False if they differ.
        """
        if self._sp_cache is None:
            return False

        difference = abs(self._get_component_sp() - self._sp_cache)
        return difference < self._motor_axis.resolution

    def has_out_of_beam_position(self):
        """
        Returns: True if this river has out of beam position set; False otherwise.
        """
        return self._out_of_beam_lookup is not None
