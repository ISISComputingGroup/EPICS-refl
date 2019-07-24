"""
Objects to help with calculating the beam path when interacting with a component. This is used for instance for the
set points or readbacks etc.
"""
from math import degrees, atan2

from ReflectometryServer.geometry import PositionAndAngle
import logging

logger = logging.getLogger(__name__)


class TrackingBeamPathCalc(object):
    """
    Calculator for the beam path when it interacts with a component that can track the beam.
    """

    def __init__(self, movement_strategy):
        """
        Initialiser.
        Args:
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovementCalc): strategy for calculating the
                interception between the movement of the component and the beam.
        """
        self._incoming_beam = PositionAndAngle(0, 0, 0)
        self._after_beam_path_update_listeners = set()
        self._after_beam_path_update_on_init_listeners = set()
        self._after_physical_move_listeners = set()
        self._after_is_changing_change_listeners = set()
        self._init_listeners = set()
        self._is_in_beam = True
        self._is_displacing = False
        self._is_rotating = False
        self._movement_strategy = movement_strategy

        self.autosaved_offset = None

        # This is used in disable mode where the incoming
        self.incoming_beam_can_change = True

        # This is the theta beam path and is used because this beam path calc is defining theta and therefore its offset
        #   will always be exact. So we use this to calculate the position of the component not the incoming beam.
        #  If it is None then this does not define theta
        self.substitute_incoming_beam_for_displacement = None

    def init_displacement_from_motor(self, value):
        """
        Sets the displacement read from the motor axis on startup.

        Params:
            value(float): The motor position
        """
        self._movement_strategy.set_displacement(value)
        self._trigger_init_listeners()  # Tell Parameter layer and Theta

    def add_init_listener(self, listener):
        """
        Add a listener which is triggered if an initial value is set
        Args:
            listener: listener to trigger after initialisation
        """
        self._init_listeners.add(listener)

    def _trigger_init_listeners(self):
        """
        Runs initialisation listeners because an initial value has been read.
        """
        for listener in self._init_listeners:
            listener()

    def add_after_is_changing_change_listener(self, listener):
        """
        Add a listener which is triggered if the changing (rotating, displacing etc) state is changed.

        Args:
            listener: listener with a single argument which is the calling calculation.
        """
        self._after_is_changing_change_listeners.add(listener)

    def _trigger_after_is_changing_change(self):
        """
        Runs all the current listeners on the changing state because something has changed.
        """
        for listener in self._after_is_changing_change_listeners:
            listener()

    def add_after_beam_path_update_listener(self, listener):
        """
        Add a listener which is triggered if the beam path is changed. For example if displacement is set or incoming
        beam is changed.
        Args:
            listener: listener with a single argument which is the calling calculation.
        """
        self._after_beam_path_update_listeners.add(listener)

    def _trigger_after_beam_path_update(self):
        """
        Runs all the current listeners on the beam path because something about it has changed.
        """
        for listener in self._after_beam_path_update_listeners:
            listener(self)

    def add_after_beam_path_update_on_init_listener(self, listener):
        """
        Add a listener which is triggered if the beam path is changed after a component reads an initial value on
        startup. For example if incoming beam is changed.
        Args:
            listener: listener with a single argument which is the calling calculation.
        """
        self._after_beam_path_update_on_init_listeners.add(listener)

    def _trigger_after_beam_path_update_on_init(self):
        """
        Runs all the current listeners because something about the beam path has changed after a component reads an
        initial value on startup.
        """
        for listener in self._after_beam_path_update_on_init_listeners:
            listener(self)

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
            self._on_set_incoming_beam(incoming_beam)
        if on_init:
            if self.autosaved_offset is not None:
                self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam, self.autosaved_offset)
            self._trigger_init_listeners()
            self._trigger_after_beam_path_update_on_init()
        else:
            self._trigger_after_beam_path_update()

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

    def set_position_relative_to_beam(self, displacement):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            displacement: the value to set away from the beam, e.g. height
        """
        self._movement_strategy.set_distance_relative_to_beam(self._incoming_beam, displacement)
        self._trigger_after_beam_path_update()

    def get_position_relative_to_beam(self):
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

    def set_displacement(self, displacement, alarm_severity, alarm_status):
        """
        Set the displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        Args:
            displacement: the displacement to set
            alarm_severity (ReflectometryServer.pv_wrapper.AlarmSeverity): severity of any alarm
            alarm_status (ReflectometryServer.pv_wrapper.AlarmCondition): the alarm status
        """
        self._movement_strategy.set_displacement(displacement)
        self._trigger_after_beam_path_update()
        self._trigger_after_physical_move_listener()

    def get_displacement(self):
        """
        Returns: The displacement of the component from the zero position, E.g. The distance along the movement
            axis of the component from the set zero position.
        """
        return self._movement_strategy.get_displacement()

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

        Params:
            on_init(Boolean): Whether this is being called on init (decides which value to use for offset)

        Returns (ReflectometryServer.geometry.Position): The position of the beam intercept in mantid coordinates.
        """
        if on_init:
            offset = self.autosaved_offset or self.get_position_relative_to_beam() or 0
        else:
            offset = self.get_position_relative_to_beam() or 0
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
        self._trigger_after_beam_path_update()
        self._trigger_after_physical_move_listener()

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
        self._trigger_after_is_changing_change()

    @property
    def is_rotating(self):
        """
        Returns: Is the angular component currently rotating
        """
        return self._is_rotating

    @is_rotating.setter
    def is_rotating(self, value):
        """
         Update the angular components rotating state and triggers the changing state listeners

         Args:
             value: the new rotating state
        """
        self._is_rotating = value
        self._trigger_after_is_changing_change()

    def add_after_physical_move_listener(self, listener):
        """
        Add a listener which is called when a move is generated from a location change not from a incoming beam path
        change. For example when a height is increased by the motor. This is used by the Theta readback to determine if
        a component has changed height.
        Args:
            listener: listener takes the source of the change
        """
        self._after_physical_move_listeners.add(listener)

    def _trigger_after_physical_move_listener(self):
        for listener in self._after_physical_move_listeners:
            listener(self)


class _BeamPathCalcWithAngle(TrackingBeamPathCalc):
    def __init__(self, movement_strategy):
        super(_BeamPathCalcWithAngle, self).__init__(movement_strategy)
        self._angle = 0.0

    def init_angle_from_motor(self, angle):
        """
        Initialise the angle of this component from a motor axis value.

        Params:
            value(float): The angle read from the motor
        """
        self._angle = angle
        self._trigger_init_listeners()

    def _set_angle(self, angle):
        """
        Set the angle
        Args:
            angle: angle to set
        """
        self._angle = angle
        self._trigger_after_beam_path_update()

    def set_angle_relative_to_beam(self, angle):
        """
        Set the angle of the component relative to the beamline
        Args:
            angle: angle to set the component at
        """
        self._set_angle(angle + self._incoming_beam.angle)

    def get_angle_relative_to_beam(self):
        """
        Returns: the angle of the component relative to the beamline
        """
        return self._angle - self._incoming_beam.angle


class BeamPathTilting(_BeamPathCalcWithAngle):
    """
    A beam path calculation which includes an angle it can tilt at. Beam path is unaffected by the angle.
    """

    def __init__(self, movement_strategy):
        super(BeamPathTilting, self).__init__(movement_strategy)

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle

    @angle.setter
    def angle(self, angle):
        """
        Updates the component angle and notifies the beam path update listener
        Args:
            angle: The modified angle
        """
        self._set_angle(angle)
        self._trigger_after_physical_move_listener()


class _BeamPathCalcReflecting(_BeamPathCalcWithAngle):
    """
    A beam path calculation which includes an angle of the component and that reflects the beam from that angle.
    This is used for theta and reflecting component.
    """

    def __init__(self, movement_strategy):
        super(_BeamPathCalcReflecting, self).__init__(movement_strategy)

    def init_angle_from_motor(self, angle):
        """
        Initialise the angle of this component from a motor axis value.

        Params:
            value(float): The angle read from the motor
        """
        super(_BeamPathCalcReflecting, self).init_angle_from_motor(angle)
        self._trigger_after_beam_path_update_on_init()

    def get_outgoing_beam(self):
        """
        Returns: the outgoing beam based on the last set incoming beam and any interaction with the component
        """
        if not self._is_in_beam:
            return self._incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angle - self._incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self._incoming_beam.angle
        return PositionAndAngle(target_position.y, target_position.z, angle)


class BeamPathCalcAngleReflecting(_BeamPathCalcReflecting):
    """
    A reflecting beam path calculation which includes an angle of the component that can be set,
    e.g. a reflecting mirror.
    """

    def __init__(self, movement_strategy):
        super(BeamPathCalcAngleReflecting, self).__init__(movement_strategy)
        self._angle = 0.0

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle

    @angle.setter
    def angle(self, angle):
        """
        Updates the component angle and notifies the beam path update listener
        Args:
            angle: The modified angle
        """
        self._set_angle(angle)
        self._trigger_after_physical_move_listener()


class BeamPathCalcThetaRBV(_BeamPathCalcReflecting):
    """
    A reflecting beam path calculator which has a read only angle based on the angle to a list of beam path
    calculations. This is used for example for Theta where the angle is the angle to the next enabled component.
    """

    def __init__(self, movement_strategy, angle_to, theta_setpoint_beam_path_calc):
        """
        Initialiser.
        Args:
            movement_strategy: movement strategy to use
            angle_to (list[(ReflectometryServer.beam_path_calc.TrackingBeamPathCalc, ReflectometryServer.beam_path_calc.TrackingBeamPathCalc)]):
                readback beam path calc on which to base the angle and setpoint on which the offset is taken
            theta_setpoint_beam_path_calc (ReflectometryServer.beam_path_calc.BeamPathCalcThetaSP)
        """
        super(BeamPathCalcThetaRBV, self).__init__(movement_strategy)
        self._angle_to = angle_to
        self.theta_setpoint_beam_path_calc = theta_setpoint_beam_path_calc
        for readback_beam_path_calc, setpoint_beam_path_calc in self._angle_to:
            readback_beam_path_calc.add_after_physical_move_listener(self._update_angle)
            setpoint_beam_path_calc.add_after_physical_move_listener(self._update_angle)
            readback_beam_path_calc.add_after_is_changing_change_listener(self._on_is_changing_change)

    def _on_is_changing_change(self):
        for readback_beam_path_calc, setpoint_beam_path_calc in self._angle_to:
            if readback_beam_path_calc.is_in_beam:
                self.is_rotating = readback_beam_path_calc.is_displacing
                self._trigger_after_is_changing_change()
                break

    def _update_angle(self, source):
        """
        A listener for the beam update from another beam calc.
        Args:
            source: the beam calc that changed
        """
        self._set_angle(self._calc_angle_from_next_component(self._incoming_beam))

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
        Function called between incoming beam having been set and the change listners being triggered.
        In this case we need to calulcate a new angle because out angle is the angle of the mirror needed to bounce the
        beam from the incoming beam to the outgoing beam.

        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        self._angle = self._calc_angle_from_next_component(incoming_beam)

    @property
    def angle(self):
        """
        Returns: the angle of the component measured clockwise from the horizon in the incoming beam direction.
        """
        return self._angle


class BeamPathCalcThetaSP(BeamPathCalcAngleReflecting):
    """
    A calculation for theta SP which takes an angle to parameter. This allows changes in theta to change the incoming
    beam on the component it is pointing at when in disable mode. It will only change the beam if the component is in
    the beam.
    """

    def __init__(self, movement_strategy, angle_to):
        """
        Initialiser.
        Args:
            movement_strategy: movement strategy to use
            angle_to (list[ReflectometryServer.beam_path_calc.TrackingBeamPathCalc]):
                beam path calc on which to base the angle
        """
        super(BeamPathCalcThetaSP, self).__init__(movement_strategy)
        self._angle_to = angle_to
        for comp in self._angle_to:
            comp.add_init_listener(self._init_listener)

    def _init_listener(self):
        """
        Initialises the theta angle. To be put on the component this theta is angled to, and triggered once that
        component has read an initial position.
        """
        self._angle = self._calc_angle_from_next_component(self._incoming_beam)
        self._trigger_init_listeners()
        self._trigger_after_beam_path_update()

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

    def _trigger_after_beam_path_update(self):
        """
        Before triggering movement, set the disabled components angle which we point at.
        This is because it will not get the altered beam path.
        """

        for angle_to in self._angle_to:
            if not angle_to.incoming_beam_can_change and angle_to.is_in_beam:
                angle_to.set_incoming_beam(self.get_outgoing_beam(), force=True)
                break

        super(BeamPathCalcThetaSP, self)._trigger_after_beam_path_update()
