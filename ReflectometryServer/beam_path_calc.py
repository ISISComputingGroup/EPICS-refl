"""
Objects to help with calculating the beam path when interacting with a component. This is used for instance for the
set points or readbacks etc.
"""
from collections import namedtuple

from math import degrees, atan2, isnan
from typing import Dict, List, Tuple

from ReflectometryServer.axis import PhysicalMoveUpdate, AxisChangingUpdate, InitUpdate, ComponentAxis, \
    BeamPathCalcAxis, AddOutOfBeamPositionEvent, AxisChangedUpdate
from ReflectometryServer.geometry import PositionAndAngle, ChangeAxis
import logging

from server_common.channel_access import maximum_severity, AlarmStatus, AlarmSeverity
from server_common.observable import observable
from ReflectometryServer.file_io import disable_mode_autosave

logger = logging.getLogger(__name__)

# Event that is triggered when the path of the beam has changed.
BeamPathUpdate = namedtuple("BeamPathUpdate", [
    "source"])  # The source of the beam path change. (the component itself)

# Event that is triggered when the path of the beam has changed as a result of being initialised from file or motor rbv.
BeamPathUpdateOnInit = namedtuple("BeamPathUpdateOnInit", [
    "source"])  # The source of the beam path change. (the component itself)


@observable(InitUpdate, AxisChangingUpdate, AxisChangedUpdate, PhysicalMoveUpdate)
class InBeamManager:
    """
    Manages the in-beam status of a component as a whole by combining information from all axes on the component that
    can be parked.
    """
    axes: Dict[ChangeAxis, ComponentAxis]

    def __init__(self):
        self.parking_axes = []

    def add_axes(self, axes):
        """
        Add all movement axes that have been defined for the host component.

        Args:
            axes (Dict[ChangeAxis, ComponentAxis]): The axes to add
        """
        for component_axis in axes.values():
            component_axis.add_listener(AddOutOfBeamPositionEvent, self._on_add_out_of_beam_position)

    def _on_add_out_of_beam_position(self, event):
        axis = event.source
        self.parking_axes.append(axis)
        axis.add_listener(AxisChangingUpdate, self._propagate_axis_event)
        axis.add_listener(AxisChangedUpdate, self._propagate_axis_event)
        axis.add_listener(InitUpdate, self._propagate_axis_event)
        axis.add_listener(PhysicalMoveUpdate, self._propagate_axis_event)

    def _propagate_axis_event(self, event):
        self.trigger_listeners(event)

    def get_is_in_beam(self):
        """
        Returns: the in beam status; in if any axis is in the beam or there are no axes to park
        """
        return any([axis.is_in_beam for axis in self.parking_axes]) or self.parking_axes == []

    def set_is_in_beam(self, is_in_beam):
        """
        Updates the components in_beam status and notifies the beam path update listener
        Args:
            is_in_beam: True if set the component to be in the beam; False otherwise
        """
        for axis in self.parking_axes:
            axis.is_in_beam = is_in_beam

    @property
    def is_changing(self):
        """
        Returns: Is any axis currently moving; if there are no axes then False
        """
        return any([axis.is_changing for axis in self.parking_axes])

    @property
    def alarm(self):
        """
        Returns:
            the alarm tuple for the axis, alarm_severity and alarm_status
        """
        alarms = [axis.alarm for axis in self.parking_axes]
        return maximum_severity(*alarms)


@observable(BeamPathUpdate, BeamPathUpdateOnInit)
class TrackingBeamPathCalc:
    """
    Calculator for the beam path when it interacts with a component that can be displaced relative to the beam.
    """
    axis: Dict[ChangeAxis, ComponentAxis]

    def __init__(self, name, movement_strategy):
        """
        Initialise.
        Args:
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovementCalc): strategy for calculating the
                interception between the movement of the component and the beam.
            name (str): name of this beam path calc (used for autosave key)
        """
        self._name = name
        self._incoming_beam = PositionAndAngle(0, 0, 0)
        self._movement_strategy = movement_strategy

        # This is used in disable mode where the incoming
        self.incoming_beam_can_change = True

        # This is the theta beam path and is used because this beam path calc is defining theta and therefore its offset
        #   will always be exact. So we use this to calculate the position of the component not the incoming beam.
        #  If it is None then this does not define theta
        self.substitute_incoming_beam_for_displacement = None

        self.in_beam_manager = InBeamManager()
        self.in_beam_manager.add_listener(PhysicalMoveUpdate, self._on_in_beam_status_update)
        self.in_beam_manager.add_listener(AxisChangedUpdate, self._on_in_beam_status_update)

        self.axis = {
            ChangeAxis.POSITION: BeamPathCalcAxis(ChangeAxis.POSITION,
                                                  self._get_position_relative_to_beam,
                                                  self._set_position_relative_to_beam,
                                                  self._get_displacement_for,
                                                  self._get_displacement,
                                                  self._displacement_update,
                                                  self._init_displacement_from_motor)
        }

    def _init_displacement_from_motor(self, value):
        """
        Sets the displacement read from the motor axis on startup.

        Args:
            value(float): The motor position
        """
        self._movement_strategy.set_displacement(value)
        self.axis[ChangeAxis.POSITION].trigger_listeners(InitUpdate())  # Tell Parameter layer and Theta

    def set_incoming_beam(self, incoming_beam, force=False, on_init=False):
        """
        Set the incoming beam for the component setpoint calculation.
        This method should respect self.incoming_beam_can_change.
        Args:
            incoming_beam(PositionAndAngle): incoming beam
            force: set the incoming beam even if incoming_beam_can_change is not true
            on_init: whether the beam was set as part of IOC initialisation
        """
        if self.incoming_beam_can_change or force:
            self._incoming_beam = incoming_beam
            if not self.incoming_beam_can_change:
                self.incoming_beam_auto_save()
            self._on_set_incoming_beam(incoming_beam, on_init=on_init)
        if on_init:
            # Beam has changed position so reapply autosave which is relative to beam, trigger beampath update init not
            # beam path update
            autosaved_value = self.axis[ChangeAxis.POSITION].autosaved_value
            if autosaved_value is not None:
                self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam, autosaved_value)
            for axis in self.axis.values():
                axis.trigger_listeners(InitUpdate())
            self.trigger_listeners(BeamPathUpdateOnInit(self))
        else:
            self.trigger_listeners(BeamPathUpdate(self))

    def _on_set_incoming_beam(self, incoming_beam, on_init):
        """
        Function called between incoming beam having been set and the change listeners being triggered. Used in classes
        which inherit this to change behaviour on set of incoming beam. Only called when the incoming beam is allowed
        to change

        Args:
            incoming_beam(PositionAndAngle): incoming beam
            on_init(bool): True for this is during init; False otherwise
        """
        pass

    def _on_in_beam_status_update(self, _):
        self.trigger_listeners(BeamPathUpdate(self))

    def get_outgoing_beam(self):
        """
        Returns the outgoing beam. This class is overridden by components which affect the beam angle.
        Returns (PositionAndAngle): the outgoing beam based on the incoming beam and any interaction with the component
        """
        return self._incoming_beam

    def calculate_beam_interception(self):
        """
        Returns: the position at the point where the components possible movement intercepts the beam (the beam is
            the theta beam if set or the incoming beam if not)
        """
        return self._movement_strategy.calculate_interception(self._theta_incoming_beam_if_set_else_incoming_beam())

    def _set_position_relative_to_beam(self, displacement):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            displacement: the value to set away from the beam, e.g. height
        """
        self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam, displacement)
        self.trigger_listeners(BeamPathUpdate(self))

    def _get_position_relative_to_beam(self):
        """

        Returns: the displacement of the component relative to the beam, E.g. The distance along the movement
            axis of the component from the intercept with the beam. Beam is theta beam if set otherwise incoming beam

        """
        return self._movement_strategy.get_distance_relative_to_beam(
            self._theta_incoming_beam_if_set_else_incoming_beam())

    def _theta_incoming_beam_if_set_else_incoming_beam(self):
        """
        If this is the component defining theta then measuring relative to the incoming beam makes no sense it will
        always be zero, so instead measure with respect to the setpoint beam. This function returns the correct beam.
        Returns: theta incoming beam if this is not None; otherwise returns incoming beam

        """
        if self.substitute_incoming_beam_for_displacement is None:
            beam = self._incoming_beam
        else:
            beam = self.substitute_incoming_beam_for_displacement
        return beam

    def _displacement_update(self, displacement):
        """
        Update value and alarms of the displacement axis. The displacement is from the zero position, E.g. The distance
            along the movement axis of the component from the set zero position.

        Args:
            displacement (float): The displacement in mantid coordinates to set the axis to
        """
        self._movement_strategy.set_displacement(displacement)
        self.trigger_listeners(BeamPathUpdate(self))

    def _get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        return self._movement_strategy.get_displacement()

    def _get_displacement_for(self, position_relative_to_beam):
        """
        Get the displacement for a given position relative to the beam
        Args:
            position_relative_to_beam (float): position to get the displacement for

        Returns (float): displacement in mantid coordinates
        """

        return self._movement_strategy.get_displacement_relative_to_beam_for(self._incoming_beam,
                                                                             position_relative_to_beam)

    def position_in_mantid_coordinates(self):
        """
        Returns (ReflectometryServer.geometry.Position): The set point position of this component in mantid coordinates.
        """
        return self._movement_strategy.position_in_mantid_coordinates()

    def get_distance_relative_to_beam_in_mantid_coordinates(self):
        """
        Returns (ReflectometryServer.geometry.Position): distance to the beam in mantid coordinates as a vector, beam
            is the theta beam if set otherwise incoming beam
        """
        return self._movement_strategy.get_distance_relative_to_beam_in_mantid_coordinates(
            self._theta_incoming_beam_if_set_else_incoming_beam())

    def intercept_in_mantid_coordinates(self, on_init=False):
        """
        Calculates the position of the intercept between the incoming beam and the movement axis of this component.

        Args:
            on_init(Boolean): Whether this is being called on initialisation

        Returns (ReflectometryServer.geometry.Position): The position of the beam intercept in mantid coordinates.
        """
        autosaved_value = self.axis[ChangeAxis.POSITION].autosaved_value
        if on_init and autosaved_value is not None:
            offset = autosaved_value
        else:
            offset = self.axis[ChangeAxis.POSITION].get_relative_to_beam() or 0
        intercept_displacement = self._get_displacement() - offset
        return self._movement_strategy.position_in_mantid_coordinates(intercept_displacement)

    @property
    def is_in_beam(self):
        """
        Returns: the in beam status
        """
        return self.in_beam_manager.get_is_in_beam()

    @is_in_beam.setter
    def is_in_beam(self, is_in_beam):
        """
        Updates the components in_beam status and notifies the beam path update listener
        Args:
            is_in_beam: True if set the component to be in the beam; False otherwise
        """
        self.in_beam_manager.set_is_in_beam(is_in_beam)
        self.trigger_listeners(BeamPathUpdate(self))
        for axis in self.axis.values():
            axis.trigger_listeners(PhysicalMoveUpdate(axis))

    def incoming_beam_auto_save(self):
        """
        Save the current incoming beam to autosave file if the incoming beam can not be changed
        i.e. only in disable mode
        """
        if not self.incoming_beam_can_change:
            disable_mode_autosave.write_parameter(self._name, self._incoming_beam)

    def init_beam_from_autosave(self):
        """
        Restore the autosaved incoming beam when autosave value is found and component is in non changing beamline mode
        i.e. only in disabled mode
        """
        if not self.incoming_beam_can_change:
            incoming_beam = disable_mode_autosave.read_parameter(self._name, None)
            if incoming_beam is None:
                incoming_beam = PositionAndAngle(0, 0, 0)
                logger.error("Incoming beam was not initialised for component {}".format(self._name))
            self.set_incoming_beam(incoming_beam, force=True, on_init=True)


class _BeamPathCalcWithAngle(TrackingBeamPathCalc):
    """
    Calculator for the beam path when it interacts with a component that can be displaced and rotated relative to the
    beam. The rotation angle is set implicitly and is read only.
    """
    def __init__(self, name, movement_strategy, is_reflecting):
        """
        Initialise.
        Args:
            name (str): name of this beam path calc (used for autosave key)
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovementCalc): strategy for calculating the
                interception between the movement of the component and the beam.
                is_reflecting (bool): Whether the component reflects or just tracks the beam.
        """
        super(_BeamPathCalcWithAngle, self).__init__(name, movement_strategy)
        self._angular_displacement = 0.0
        self._is_reflecting = is_reflecting

    def _get_angular_displacement(self):
        """
        Returns: the angle of the component relative to the natural (straight through) beam measured clockwise from the
            horizon in the incoming beam direction.
        """
        return self._angular_displacement

    def _set_angular_displacement(self, angle):
        """
        Set the angular displacement relative to the straight-through beam.
        Args:
            angle: angle to set
        """
        self._angular_displacement = angle
        if self._is_reflecting:
            self.trigger_listeners(BeamPathUpdate(self))

    def _set_angle_relative_to_beam(self, angle):
        """
        Set the angle of the component relative to the beamline
        Args:
            angle: angle to set the component at
        """
        self._set_angular_displacement(self._get_angle_for(angle))

    def _get_angle_relative_to_beam(self):
        """
        Returns (float): the angle of the component relative to the incoming beam
        """
        return self._angular_displacement - self._incoming_beam.angle

    def _get_angle_for(self, position_relative_to_beam):
        """
        Get the displacement for a given angle relative to the beam
        Args:
            position_relative_to_beam (float): position to get the displacement for

        Returns (float): displacement in mantid coordinates
        """
        return position_relative_to_beam + self._incoming_beam.angle

    def get_outgoing_beam(self):
        """
        Returns: the outgoing beam based on the last set incoming beam and any interaction with the component
        """
        if not self.is_in_beam or not self._is_reflecting:
            return self._incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angular_displacement - self._incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self._incoming_beam.angle
        outgoing_beam = PositionAndAngle(target_position.y, target_position.z, angle)
        return outgoing_beam


class SettableBeamPathCalcWithAngle(_BeamPathCalcWithAngle):
    """
    Calculator for the beam path when it interacts with a component that can be displaced and rotated relative to the
    beam, and where the angle can be both read and set explicitly.
    """
    def __init__(self, name, movement_strategy, is_reflecting):
        super(SettableBeamPathCalcWithAngle, self).__init__(name, movement_strategy, is_reflecting)
        self.axis[ChangeAxis.ANGLE] = BeamPathCalcAxis(ChangeAxis.ANGLE,
                                                       self._get_angle_relative_to_beam,
                                                       self._set_angle_relative_to_beam,
                                                       self._get_angle_for,
                                                       self._get_angular_displacement,
                                                       self._set_angular_displacement,
                                                       self._init_angle_from_motor)

    def _init_angle_from_motor(self, angle):
        """
        Initialise the angle of this component from a motor axis value.

        Args:
            angle(float): The angle read from the motor
        """
        self._angular_displacement = angle
        self.axis[ChangeAxis.ANGLE].trigger_listeners(InitUpdate())
        if self._is_reflecting:
            self.trigger_listeners(BeamPathUpdateOnInit(self))

    def _on_set_incoming_beam(self, incoming_beam, on_init):
        if on_init:
            # Beam has changed position so reapply autosave which is relative to beam, caller will trigger beampath
            # update init so this should not trigger beam path update
            autosaved_value = self.axis[ChangeAxis.ANGLE].autosaved_value
            if autosaved_value is not None:
                self._angular_displacement = self._get_angle_for(autosaved_value)


class BeamPathCalcThetaRBV(_BeamPathCalcWithAngle):
    """
    A reflecting beam path calculator which has a read only angle based on the angle to a list of beam path
    calculations. This is used for example for Theta where the angle is the angle to the next enabled component.
    """
    _angle_to: List[Tuple[TrackingBeamPathCalc, TrackingBeamPathCalc, ChangeAxis]]

    def __init__(self, name, movement_strategy, theta_setpoint_beam_path_calc):
        """
        Initialise.
        Args:
            name (str): name of this beam path calc (used for autosave key)
            movement_strategy: movement strategy to use
            theta_setpoint_beam_path_calc (ReflectometryServer.beam_path_calc.BeamPathCalcThetaSP)


        """
        super(BeamPathCalcThetaRBV, self).__init__(name, movement_strategy, is_reflecting=True)
        self.axis[ChangeAxis.ANGLE] = BeamPathCalcAxis(ChangeAxis.ANGLE,
                                                       self._get_angle_relative_to_beam,
                                                       self._set_angle_relative_to_beam)

        self.axis[ChangeAxis.ANGLE].can_define_axis_position_as = False
        self._angle_to = []
        self.theta_setpoint_beam_path_calc = theta_setpoint_beam_path_calc
        self._add_pre_trigger_function(BeamPathUpdate, self._set_incoming_beam_at_next_angled_to_component)

    def add_angle_to(self, readback_beam_path_calc, setpoint_beam_path_calc, axis):
        """
        Add angle to these beam path calcs and setpoints on this axis on which to base the angle and setpoint on which
            the offset is taken. This add it to the end of the list.
        Args:
            readback_beam_path_calc (ReflectometryServer.beam_path_calc.TrackingBeamPathCalc): readback calc
            setpoint_beam_path_calc (ReflectometryServer.beam_path_calc.TrackingBeamPathCalc): set point calc needed for
                the offset from the beam that should be used
            axis (ChangeAxis.POSITION|ChangeAxis.ANGLE): axis on which to base the angle to
        """
        self._angle_to.append((readback_beam_path_calc, setpoint_beam_path_calc, axis))
        # add to the physical change for the rbv so that we don't get an infinite loop
        readback_beam_path_calc.axis[axis].add_listener(PhysicalMoveUpdate, self._angle_update)
        readback_beam_path_calc.in_beam_manager.add_listener(PhysicalMoveUpdate, self._angle_update)
        # add to beamline change of set point because no loop is created from the setpoint action
        setpoint_beam_path_calc.add_listener(BeamPathUpdate, self._angle_update)
        readback_beam_path_calc.axis[axis].add_listener(AxisChangingUpdate, self._on_is_changing_change)
        readback_beam_path_calc.in_beam_manager.add_listener(AxisChangingUpdate, self._on_is_changing_change)

    def _on_is_changing_change(self, _):
        """
        Updates the changing state of this component. Theta is changing if the first in beam component is changing or
        if there are no in beam components and one out of beam component is changing

        Args:
            _ (AxisChangingUpdate): The update event
        """
        theta_is_changing = False
        for readback_beam_path_calc, setpoint_beam_path_calc, axis in self._angle_to:
            is_changing = readback_beam_path_calc.axis[axis].is_changing
            theta_is_changing = theta_is_changing or is_changing
            if readback_beam_path_calc.is_in_beam:
                theta_is_changing = is_changing
                break

        self.axis[ChangeAxis.ANGLE].is_changing = theta_is_changing

    def _angle_update(self, _):
        self._set_angular_displacement(self._set_up_next_component_and_return_angle_set_by_it(self._incoming_beam))

    def _set_up_next_component_and_return_angle_set_by_it(self, incoming_beam):
        """
        Finds the component to point theta at (i.e. first in beam component). Sets this up as defining theta and returns
        the angle this needs theta to be.

        Also sets alarms for current axis, sets beampath on selected_component and clears it for non-selected

        Returns: the angle in mantid coordinates that a mirror would be needed to be placed at to reflect the
            beam to the next component or reflect the beam at the given angle; or nan if there isn't a component in the
            beam
        """

        # clear previous incoming theta beam on all components
        for readback_beam_path_calc, _, _ in self._angle_to:
            readback_beam_path_calc.substitute_incoming_beam_for_displacement = None

        for readback_beam_path_calc, set_point_beam_path_calc, axis in self._angle_to:
            if readback_beam_path_calc.is_in_beam:
                if axis == ChangeAxis.POSITION:
                    other_pos = readback_beam_path_calc.position_in_mantid_coordinates()
                    set_point_offset = set_point_beam_path_calc.get_distance_relative_to_beam_in_mantid_coordinates()
                    this_pos = self._movement_strategy.calculate_interception(incoming_beam)

                    opp = other_pos.y - set_point_offset.y - this_pos.y
                    adj = other_pos.z - set_point_offset.z - this_pos.z
                    # x = degrees(atan2(opp, adj)) is angle in room co-ords to component
                    # x = x - incoming_beam.angle : is 2 theta
                    # x = x / 2.0: is theta
                    # x + incoming_beam.angle: angle of sample in room coordinate

                    angle_of_outgoing_beam = degrees(atan2(opp, adj))
                elif axis == ChangeAxis.ANGLE:
                    # rbv should not include setpoint offset angle
                    other_angle = readback_beam_path_calc.axis[ChangeAxis.ANGLE].get_displacement()
                    other_setpoint_offset = set_point_beam_path_calc.axis[ChangeAxis.ANGLE].get_relative_to_beam()
                    angle_of_outgoing_beam = other_angle - other_setpoint_offset
                else:
                    raise RuntimeError("Theta can not depend on the {} axis".format(axis))

                angle = (angle_of_outgoing_beam - incoming_beam.angle) / 2.0 + incoming_beam.angle
                # set the beam path for the selected component
                readback_beam_path_calc.substitute_incoming_beam_for_displacement = \
                    self.theta_setpoint_beam_path_calc.get_outgoing_beam()
                # set alarms from component setting the angle
                alarm_severity, alarm_status = readback_beam_path_calc.axis[axis].alarm
                self.axis[ChangeAxis.ANGLE].set_alarm(alarm_severity, alarm_status)

                break
        else:
            angle = float("NaN")
            self.axis[ChangeAxis.ANGLE].set_alarm(AlarmSeverity.Major, AlarmStatus.Link)
        return angle

    def _on_set_incoming_beam(self, incoming_beam, on_init):
        """
        Function called between incoming beam having been set and the change listeners being triggered.
        In this case we need to calculate a new angle because out angle is the angle of the mirror needed to bounce the
        beam from the incoming beam to the outgoing beam.

        Args:
            incoming_beam(PositionAndAngle): incoming beam
            on_init(bool): True if during initialisation
        """
        self._angular_displacement = self._set_up_next_component_and_return_angle_set_by_it(incoming_beam)

    def _set_incoming_beam_at_next_angled_to_component(self):
        """
        Sets the incoming beam at the next disabled component in beam that this theta component is angled to.
        """
        for readback_beam_path_calc, _, _ in self._angle_to:
            if not readback_beam_path_calc.incoming_beam_can_change and readback_beam_path_calc.is_in_beam:
                readback_beam_path_calc.set_incoming_beam(self.get_outgoing_beam(), force=True)
                break


class BeamPathCalcThetaSP(SettableBeamPathCalcWithAngle):
    """
    A calculation for theta SP which takes an angle to parameter. This allows changes in theta to change the incoming
    beam on the component it is pointing at when in disable mode. It will only change the beam if the component is in
    the beam.
    """

    def __init__(self, name, movement_strategy):
        """
        Initialise.
        Args:
            name (str): name of this beam path calc (used for autosave key)
            movement_strategy: movement strategy to use
        """
        super(BeamPathCalcThetaSP, self).__init__(name, movement_strategy, is_reflecting=True)
        self._angle_to = []
        self._add_pre_trigger_function(BeamPathUpdate, self._set_incoming_beam_at_next_angled_to_component)

    def add_angle_to(self, beam_path_calc, axis):
        """
        Add beam path calc that will be used to initialise setpoint
        Args:
            beam_path_calc (ReflectometryServer.beam_path_calc.TrackingBeamPathCalc): calc to use
            axis (ChangeAxis.POSITION|ChangeAxis.ANGLE):  axis to base angle on

        Returns:

        """
        self._angle_to.append((beam_path_calc, axis))
        beam_path_calc.axis[axis].add_listener(InitUpdate, self._init_listener)
        beam_path_calc.in_beam_manager.add_listener(InitUpdate, self._init_listener)

    def _init_listener(self, _):
        """
        Initialises the theta angle. Listens on the component(s) this theta is angled to, and is triggered once that
        component has read an initial position.

        Args:
            _: The init update event
        """
        autosaved_value = self.axis[ChangeAxis.ANGLE].autosaved_value
        if autosaved_value is None:
            angle_to_init = self._calc_angle_from_next_component(self._incoming_beam)
            self._angular_displacement = 0 if isnan(angle_to_init) else angle_to_init

        else:
            self._angular_displacement = self._incoming_beam.angle + autosaved_value

        self.axis[ChangeAxis.ANGLE].trigger_listeners(InitUpdate())
        self.trigger_listeners(BeamPathUpdate(self))

    def _calc_angle_from_next_component(self, incoming_beam):
        """
        Calculates the theta angle based on the position of the theta component and the beam intercept or angle of the
        next component on the beam it is angled to.

        Returns: half the angle to the next enabled beam path calc, or nan if there isn't one.
        """
        for setpoint_beam_path_calc, axis in self._angle_to:
            if setpoint_beam_path_calc.is_in_beam:
                if axis == ChangeAxis.POSITION:
                    other_pos = setpoint_beam_path_calc.intercept_in_mantid_coordinates(on_init=True)
                    this_pos = self._movement_strategy.calculate_interception(incoming_beam)

                    opp = other_pos.y - this_pos.y
                    adj = other_pos.z - this_pos.z
                    # x = degrees(atan2(opp, adj)) is angle in room co-ords to component
                    # x = x - incoming_beam.angle : is 2 theta
                    # x = x / 2.0: is theta
                    # x + incoming_beam.angle: angle of sample in room coordinate

                    angle_of_outgoing_beam = degrees(atan2(opp, adj))
                elif axis == ChangeAxis.ANGLE:
                    angle_of_outgoing_beam = setpoint_beam_path_calc.axis[ChangeAxis.ANGLE].get_displacement()
                    # if there is an auto saved offset then take this off before calculating theta
                    offset = setpoint_beam_path_calc.axis[ChangeAxis.ANGLE].autosaved_value
                    if offset is not None:
                        angle_of_outgoing_beam -= offset
                else:
                    raise RuntimeError("Can not set theta angle based on {} axis".format(axis))

                angle = (angle_of_outgoing_beam - incoming_beam.angle) / 2.0 + incoming_beam.angle
                break
        else:
            angle = float("NaN")
        return angle

    def _set_incoming_beam_at_next_angled_to_component(self):
        """
        Sets the incoming beam at the next disabled component in beam that this theta component is angled to.
        """
        for angle_to, axis in self._angle_to:
            if not angle_to.incoming_beam_can_change and angle_to.is_in_beam:
                angle_to.set_incoming_beam(self.get_outgoing_beam(), force=True)
                break
