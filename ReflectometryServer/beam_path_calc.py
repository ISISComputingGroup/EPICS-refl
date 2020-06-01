"""
Objects to help with calculating the beam path when interacting with a component. This is used for instance for the
set points or readbacks etc.
"""
from collections import namedtuple
from math import degrees, atan2

from ReflectometryServer.geometry import PositionAndAngle, ChangeAxis
import logging

from server_common.observable import observable
from ReflectometryServer.file_io import disable_mode_autosave

logger = logging.getLogger(__name__)

# Event that is triggered when the path of the beam has changed.
BeamPathUpdate = namedtuple("BeamPathUpdate", [
    "source"])  # The source of the beam path change. (the component itself)

# Event that is triggered when the path of the beam has changed as a result of being initialised from file or motor rbv.
BeamPathUpdateOnInit = namedtuple("BeamPathUpdateOnInit", [
    "source"])  # The source of the beam path change. (the component itself)

# Event that is triggered when the physical position of this component changes.
PhysicalMoveUpdate = namedtuple("PhysicalMoveUpdate", [
    "source"])  # The source of the beam path change. (the component itself)

# Event that is triggered when the changing state of the component is updated (i.e. it starts or stops moving)
ComponentChangingUpdate = namedtuple("ComponentChangingUpdate", [])

# Event that is triggered when the position or angle of the beam path calc gets an initial value.
InitUpdate = namedtuple("InitUpdate", [])


class BeamPathCalcAxis(object):
    """
    Encapsulate functionality of axis into a single class
    """
    def __init__(self, get_relative_to_beam, set_relative_to_beam, get_displacement_for):
        """
        Initialiser.
        Args:
            get_relative_to_beam: function returning this axis position relative to the components incoming beam
            set_relative_to_beam: function setting this axis position relative to the components incoming beam
            get_displacement_for: get a displacement for a position relative to the beam
        """
        self._get_relative_to_beam = get_relative_to_beam
        self._set_relative_to_beam = set_relative_to_beam
        self._get_displacement_for = get_displacement_for
        self._alarm = (None, None)

    def get_relative_to_beam(self):
        """
        Returns: position relative to the incoming beam
        """
        return self._get_relative_to_beam()

    def set_relative_to_beam(self, value):
        """
        Set a axis value relative to the beam, e.g. position relative to the beam.
        Args:
            value: value to set
        """
        return self._set_relative_to_beam(value)

    def get_displacement_for(self, relative_to_beam):
        """
        Given the position relative to the beam return the positon in mantid coordinates
        Args:
            relative_to_beam: position relative to the beam

        Returns:
            displacement in mantid coordinates
        """
        return self._get_displacement_for(relative_to_beam)

    @property
    def alarm(self):
        """
        Returns:
            the alarm tuple for the axis, alarm_severity and alarm_status
        """
        return self._alarm

    def set_alarm(self, alarm_severity, alarm_status):
        """
        Update the alarm info for the angle axis of this component.

        Args:
            alarm_severity (ReflectometryServer.pv_wrapper.AlarmSeverity): severity of any alarm
            alarm_status (ReflectometryServer.pv_wrapper.AlarmCondition): the alarm status
        """
        self._alarm = (alarm_severity, alarm_status)


@observable(BeamPathUpdate, BeamPathUpdateOnInit, PhysicalMoveUpdate, ComponentChangingUpdate, InitUpdate)
class TrackingBeamPathCalc(object):
    """
    Calculator for the beam path when it interacts with a component that can be displaced relative to the beam.
    """

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
        self._is_in_beam = True
        self._is_displacing = False
        self._movement_strategy = movement_strategy

        # Autosaved value for each axis; if not set is not in dictionary
        self.autosaved_value = {}

        # This is used in disable mode where the incoming
        self.incoming_beam_can_change = True

        # This is the theta beam path and is used because this beam path calc is defining theta and therefore its offset
        #   will always be exact. So we use this to calculate the position of the component not the incoming beam.
        #  If it is None then this does not define theta
        self.substitute_incoming_beam_for_displacement = None

        self.axis = {
            ChangeAxis.POSITION: BeamPathCalcAxis(self._get_position_relative_to_beam,
                                                  self._set_position_relative_to_beam,
                                                  self._get_displacement_for)
        }

    def init_displacement_from_motor(self, value):
        """
        Sets the displacement read from the motor axis on startup.

        Args:
            value(float): The motor position
        """
        self._movement_strategy.set_displacement(value)
        self.trigger_listeners(InitUpdate())  # Tell Parameter layer and Theta

    def add_init_listener(self, listener):
        """
        Add a listener which is triggered if an initial value is set
        Args:
            listener: listener to trigger after initialisation
        """
        self._init_listeners.add(listener)

    def add_after_is_changing_change_listener(self, listener):
        """
        Add a listener which is triggered if the changing (rotating, displacing etc) state is changed.

        Args:
            listener: listener with a single argument which is the calling calculation.
        """
        self._after_is_changing_change_listeners.add(listener)

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
            self._on_set_incoming_beam(incoming_beam)
        if on_init:
            if ChangeAxis.POSITION in self.autosaved_value:
                self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam,
                                                                      self.autosaved_value[ChangeAxis.POSITION])
            self.trigger_listeners(InitUpdate())
            self.trigger_listeners(BeamPathUpdateOnInit(self))
        else:
            self.trigger_listeners(BeamPathUpdate(self))

    def _on_set_incoming_beam(self, incoming_beam):
        """
        Function called between incoming beam having been set and the change listeners being triggered. Used in classes
        which inherit this to change behaviour on set of incoming beam. Only called when the incoming beam is allowed
        to change

        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        pass

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

    def displacement_update(self, update):
        """
        Update value and alarms of the displacement axis.

        Args:
            update (ReflectometryServer.ioc_driver.CorrectedReadbackUpdate): The PV update for this axis.
        """
        self.axis[ChangeAxis.POSITION].set_alarm(update.alarm_severity, update.alarm_status)
        self.set_displacement(update.value)

    def set_displacement(self, displacement):
        """
        Set the displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        Args:
            displacement: the displacement to set
        """
        self._movement_strategy.set_displacement(displacement)
        self.trigger_listeners(BeamPathUpdate(self))
        self.trigger_listeners(PhysicalMoveUpdate(self))

    def get_displacement(self):
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
        if on_init and ChangeAxis.POSITION in self.autosaved_value:
            offset = self.autosaved_value[ChangeAxis.POSITION]
        else:
            offset = self.axis[ChangeAxis.POSITION].get_relative_to_beam() or 0
        intercept_displacement = self.get_displacement() - offset
        return self._movement_strategy.position_in_mantid_coordinates(intercept_displacement)

    @property
    def is_in_beam(self):
        """
        Returns: the enabled status
        """
        return self._is_in_beam

    @is_in_beam.setter
    def is_in_beam(self, is_in_beam):
        """
        Updates the components in_beam status and notifies the beam path update listener
        Args:
            is_in_beam: True if set the component to be in the beam; False otherwise
        """
        self._is_in_beam = is_in_beam
        self.trigger_listeners(BeamPathUpdate(self))
        self.trigger_listeners(PhysicalMoveUpdate(self))

    @property
    def is_displacing(self):
        """
        Returns: Is the displacement component currently displacing
        """
        return self._is_displacing

    @is_displacing.setter
    def is_displacing(self, value):
        """
         Update the displacement component displacing state and triggers the changing state listeners

         Args:
             value: the new displacing state
        """
        self._is_displacing = value
        self.trigger_listeners(ComponentChangingUpdate())

    def incoming_beam_auto_save(self):
        """
        Save the current incoming beam to autosave file if the incoming beam can not be changed
        i.e. only in disable mode
        """
        if not self.incoming_beam_can_change:
            disable_mode_autosave.write_parameter(self._name, self._incoming_beam)

    def init_from_autosave(self):
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
        self._is_rotating = False
        self._is_reflecting = is_reflecting
        self.axis[ChangeAxis.ANGLE] = BeamPathCalcAxis(self._get_angle_relative_to_beam,
                                                       self._set_angle_relative_to_beam,
                                                       self._get_angle_for)

    def get_angular_displacement(self):
        """
        Returns: the angle of the component relative to the natural (straight through) beam measured clockwise from the
            horizon in the incoming beam direction.
        """
        return self._angular_displacement

    @property
    def is_rotating(self):
        """
        Returns: Is the component with angle currently rotating
        """
        return self._is_rotating

    @is_rotating.setter
    def is_rotating(self, value):
        """
         Update the rotating state of the component with angle and notifies relevant listeners

         Args:
             value: the new rotating state
        """
        self._is_rotating = value
        self.trigger_listeners(ComponentChangingUpdate())

    def init_angle_from_motor(self, angle):
        """
        Initialise the angle of this component from a motor axis value.

        Args:
            angle(float): The angle read from the motor
        """
        self._angular_displacement = angle
        self.trigger_listeners(InitUpdate())
        if self._is_reflecting:
            self.trigger_listeners(BeamPathUpdateOnInit(self))

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
        if not self._is_in_beam or not self._is_reflecting:
            return self._incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angular_displacement - self._incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self._incoming_beam.angle
        return PositionAndAngle(target_position.y, target_position.z, angle)


class SettableBeamPathCalcWithAngle(_BeamPathCalcWithAngle):
    """
    Calculator for the beam path when it interacts with a component that can be displaced and rotated relative to the
    beam, and where the angle can be both read and set explicitly.
    """
    def __init__(self, name, movement_strategy, is_reflecting):
        super(SettableBeamPathCalcWithAngle, self).__init__(name, movement_strategy, is_reflecting)

    def angle_update(self, update):
        """
        Update value and alarms of the angle axis.

        Args:
            update (ReflectometryServer.ioc_driver.CorrectedReadbackUpdate): The PV update for this axis.
        """
        self.axis[ChangeAxis.ANGLE].set_alarm(update.alarm_severity, update.alarm_status)
        self.set_angular_displacement(update.value)

    def set_angular_displacement(self, angle):
        """
        Updates the component angle and notifies the beam path update listener
        Args:
            angle: The modified angle
        """
        self._set_angular_displacement(angle)
        self.trigger_listeners(PhysicalMoveUpdate(self))


class BeamPathCalcThetaRBV(_BeamPathCalcWithAngle):
    """
    A reflecting beam path calculator which has a read only angle based on the angle to a list of beam path
    calculations. This is used for example for Theta where the angle is the angle to the next enabled component.
    """

    def __init__(self, name, movement_strategy, theta_setpoint_beam_path_calc, angle_to):
        """
        Initialise.
        Args:
            name (str): name of this beam path calc (used for autosave key)
            movement_strategy: movement strategy to use
            theta_setpoint_beam_path_calc (ReflectometryServer.beam_path_calc.BeamPathCalcThetaSP)
            angle_to (list[(ReflectometryServer.beam_path_calc.TrackingBeamPathCalc, ReflectometryServer.beam_path_calc.TrackingBeamPathCalc)]):
                readback beam path calc on which to base the angle and setpoint on which the offset is taken

        """
        super(BeamPathCalcThetaRBV, self).__init__(name, movement_strategy, is_reflecting=True)
        self._angle_to = angle_to
        self.theta_setpoint_beam_path_calc = theta_setpoint_beam_path_calc
        self._add_pre_trigger_function(BeamPathUpdate, self._set_incoming_beam_at_next_angled_to_component)

        for readback_beam_path_calc, setpoint_beam_path_calc in self._angle_to:
            # add to the physical change for the rbv so that we don't get an infinite loop
            readback_beam_path_calc.add_listener(PhysicalMoveUpdate, self.angle_update)
            # add to beamline change of set point because no loop is created from the setpoint action
            setpoint_beam_path_calc.add_listener(BeamPathUpdate, self.angle_update)
            readback_beam_path_calc.add_listener(ComponentChangingUpdate, self._on_is_changing_change)

    def _on_is_changing_change(self, update):
        """
        Updates the changing state of this component.

        Args:
            update (ComponentChangingUpdate): The update event
        """
        for readback_beam_path_calc, setpoint_beam_path_calc in self._angle_to:
            if readback_beam_path_calc.is_in_beam:
                self.is_rotating = readback_beam_path_calc.is_displacing
                self.trigger_listeners(ComponentChangingUpdate())
                break

    def angle_update(self, update):
        """
        A listener for the beam update from another beam calc.
        Args:
            update (PhysicalMoveUpdate): The update event
        """
        alarm_severity, alarm_status = update.source.axis[ChangeAxis.POSITION].alarm
        self.axis[ChangeAxis.ANGLE].set_alarm(alarm_severity, alarm_status)
        self._set_angular_displacement(self._calc_angle_from_next_component(self._incoming_beam))

    def _calc_angle_from_next_component(self, incoming_beam):
        """
        Calculates the angle needed for a mirror to be position to reflect the incoming beam to the components position.

        Returns: half the angle to the next enabled beam path calc, or nan if there isn't one.
        """

        # clear previous incoming theta beam on all components
        for readback_beam_path_calc, _ in self._angle_to:
            readback_beam_path_calc.substitute_incoming_beam_for_displacement = None

        for readback_beam_path_calc, set_point_beam_path_calc in self._angle_to:
            if readback_beam_path_calc.is_in_beam:
                other_pos = readback_beam_path_calc.position_in_mantid_coordinates()
                set_point_offset = set_point_beam_path_calc.get_distance_relative_to_beam_in_mantid_coordinates()
                this_pos = self._movement_strategy.calculate_interception(incoming_beam)

                opp = other_pos.y - set_point_offset.y - this_pos.y
                adj = other_pos.z - set_point_offset.z - this_pos.z
                # x = degrees(atan2(opp, adj)) is angle in room co-ords to component
                # x = x - incoming_beam.angle : is 2 theta
                # x = x / 2.0: is theta
                # x + incoming_beam.angle: angle of sample in room coordinate

                angle = (degrees(atan2(opp, adj)) - incoming_beam.angle) / 2.0 + incoming_beam.angle

                readback_beam_path_calc.substitute_incoming_beam_for_displacement = \
                    self.theta_setpoint_beam_path_calc.get_outgoing_beam()
                break
        else:
            angle = float("NaN")
        return angle

    def _on_set_incoming_beam(self, incoming_beam):
        """
        Function called between incoming beam having been set and the change listeners being triggered.
        In this case we need to calculate a new angle because out angle is the angle of the mirror needed to bounce the
        beam from the incoming beam to the outgoing beam.

        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        self._angular_displacement = self._calc_angle_from_next_component(incoming_beam)

    def _set_incoming_beam_at_next_angled_to_component(self):
        """
        Sets the incoming beam at the next disabled component in beam that this theta component is angled to.
        """
        for readback_beam_path_calc, set_point_beam_path_calc in self._angle_to:
            if not readback_beam_path_calc.incoming_beam_can_change and readback_beam_path_calc.is_in_beam:
                readback_beam_path_calc.set_incoming_beam(self.get_outgoing_beam(), force=True)
                break


class BeamPathCalcThetaSP(SettableBeamPathCalcWithAngle):
    """
    A calculation for theta SP which takes an angle to parameter. This allows changes in theta to change the incoming
    beam on the component it is pointing at when in disable mode. It will only change the beam if the component is in
    the beam.
    """

    def __init__(self, name, movement_strategy, angle_to):
        """
        Initialise.
        Args:
            name (str): name of this beam path calc (used for autosave key)
            movement_strategy: movement strategy to use
            angle_to (list[ReflectometryServer.beam_path_calc.TrackingBeamPathCalc]):
                beam path calc on which to base the angle

        """
        super(BeamPathCalcThetaSP, self).__init__(name, movement_strategy, is_reflecting=True)
        self._angle_to = angle_to
        for comp in self._angle_to:
            comp.add_listener(InitUpdate, self._init_listener)
        self._add_pre_trigger_function(BeamPathUpdate, self._set_incoming_beam_at_next_angled_to_component)

    def _init_listener(self, update):
        """
        Initialises the theta angle. Listens on the component(s) this theta is angled to, and is triggered once that
        component has read an initial position.

        Args:
            update (InitUpdate): The update event
        """
        if ChangeAxis.ANGLE in self.autosaved_value:
            self._angular_displacement = self._incoming_beam.angle + self.autosaved_value[ChangeAxis.ANGLE]
        else:
            self._angular_displacement = self._calc_angle_from_next_component(self._incoming_beam)

        self.trigger_listeners(InitUpdate())
        self.trigger_listeners(BeamPathUpdate(self))

    def _calc_angle_from_next_component(self, incoming_beam):
        """
        Calculates the theta angle based on the position of the theta component and the beam intercept of the next
        component on the beam it is angled to.

        Returns: half the angle to the next enabled beam path calc, or nan if there isn't one.
        """
        for setpoint_beam_path_calc in self._angle_to:
            if setpoint_beam_path_calc.is_in_beam:
                other_pos = setpoint_beam_path_calc.intercept_in_mantid_coordinates(on_init=True)
                this_pos = self._movement_strategy.calculate_interception(incoming_beam)

                opp = other_pos.y - this_pos.y
                adj = other_pos.z - this_pos.z
                # x = degrees(atan2(opp, adj)) is angle in room co-ords to component
                # x = x - incoming_beam.angle : is 2 theta
                # x = x / 2.0: is theta
                # x + incoming_beam.angle: angle of sample in room coordinate

                angle = (degrees(atan2(opp, adj)) - incoming_beam.angle) / 2.0 + incoming_beam.angle
                break
        else:
            angle = float("NaN")
        return angle

    def _set_incoming_beam_at_next_angled_to_component(self):
        """
        Sets the incoming beam at the next disabled component in beam that this theta component is angled to.
        """
        for angle_to in self._angle_to:
            if not angle_to.incoming_beam_can_change and angle_to.is_in_beam:
                angle_to.set_incoming_beam(self.get_outgoing_beam(), force=True)
                break
