"""
Components on a beam
"""
from math import atan, cos, tan, radians, degrees
import logging

from ReflectometryServer.beam_path_calc import TrackingBeamPathCalc, SettableBeamPathCalcWithAngle, \
    BeamPathCalcThetaRBV, BeamPathCalcThetaSP
from ReflectometryServer.axis import DirectCalcAxis, AxisChangedUpdate, \
    AxisChangingUpdate, PhysicalMoveUpdate, SetRelativeToBeamUpdate, DefineValueAsEvent, InitUpdate
from ReflectometryServer.ioc_driver import CorrectedReadbackUpdate
from ReflectometryServer.movement_strategy import LinearMovementCalc
from ReflectometryServer.geometry import ChangeAxis, PositionAndAngle
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo, Severity
from server_common.channel_access import maximum_severity

logger = logging.getLogger(__name__)


class Component:
    """
    Base object for all components that can sit on a beam line
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        self._name = name
        self._init_beam_path_calcs(setup)
        for axis_to_add in [ChangeAxis.PHI, ChangeAxis.CHI, ChangeAxis.PSI, ChangeAxis.TRANS, ChangeAxis.HEIGHT]:
            self._beam_path_set_point.axis[axis_to_add] = DirectCalcAxis(axis_to_add)
            self._beam_path_rbv.axis[axis_to_add] = DirectCalcAxis(axis_to_add)

        # Do this after all ChangeAxis have been defined for this component
        self._beam_path_rbv.in_beam_manager.add_axes(self._beam_path_rbv.axis)
        self._beam_path_set_point.in_beam_manager.add_axes(self._beam_path_set_point.axis)

    def __repr__(self):
        return "{}({} beampath sp:{!r}, beampath rbv:{!r})), ".format(
            self.__class__.__name__, self._name, self._beam_path_set_point, self._beam_path_rbv)

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = TrackingBeamPathCalc("{}_sp".format(self.name), LinearMovementCalc(setup))
        self._beam_path_rbv = TrackingBeamPathCalc("{}_rbv".format(self.name), LinearMovementCalc(setup))

    @property
    def name(self):
        """
        Returns: Name of the component
        """
        return self._name

    @property
    def beam_path_set_point(self):
        """
        The beam path calculation for the set points. This is readonly and can only be set during construction
        Returns:
            (TrackingBeamPathCalc|SettableBeamPathCalcWithAngle|BeamPathCalcThetaRBV|BeamPathCalcThetaSP|BeamPathCalcAngleReflecting):
                set points beam path calculation
        """
        return self._beam_path_set_point

    @property
    def beam_path_rbv(self):
        """
        The beam path calculation for the read backs. This is readonly and can only be set during construction
        Returns:
            (TrackingBeamPathCalc|SettableBeamPathCalcWithAngle|BeamPathCalcThetaRBV|BeamPathCalcThetaSP|BeamPathCalcAngleReflecting):
                read backs beam path calculation

        """
        return self._beam_path_rbv

    def set_incoming_beam_can_change(self, can_change, on_init=False):
        """
        Set whether the incoming beam can be changed on a component. This is used in disable mode where the incoming
        beam can not be changed.
        Args:
            can_change: True if the incoming beam can changed; False if it is static
            on_init: True if initialising the beam can change parameter; False otherwise
        """
        self._beam_path_set_point.incoming_beam_can_change = can_change
        self._beam_path_rbv.incoming_beam_can_change = can_change

        if on_init:
            self._beam_path_set_point.init_beam_from_autosave()
            self._beam_path_rbv.init_beam_from_autosave()
        else:
            self._beam_path_set_point.incoming_beam_auto_save()
            self._beam_path_rbv.incoming_beam_auto_save()


class TiltingComponent(Component):
    """
    Component which can tilt.
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(TiltingComponent, self).__init__(name, setup)

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name), LinearMovementCalc(setup),
                                                                  is_reflecting=False)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name), LinearMovementCalc(setup),
                                                            is_reflecting=False)


class ReflectingComponent(Component):
    """
    Components which reflects the beam from an reflecting surface at an angle.
    """
    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(ReflectingComponent, self).__init__(name, setup)

    def _init_beam_path_calcs(self, setup):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name), LinearMovementCalc(setup),
                                                                  is_reflecting=True)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name), LinearMovementCalc(setup),
                                                            is_reflecting=True)


class ThetaComponent(ReflectingComponent):
    """
    Components which reflects the beam from an reflecting surface at an angle.
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(ReflectingComponent, self).__init__(name, setup)

    def add_angle_to(self, component):
        """
        Add component which defines the theta angle by it position. This creates an internal list ordered by insertion
            order. First enabled component is used to define theta.
        Args:
            component (ReflectometryServer.components.Component): component that defines theta

        """
        self._beam_path_set_point.add_angle_to(component.beam_path_set_point, ChangeAxis.POSITION)
        self._beam_path_rbv.add_angle_to(component.beam_path_rbv, component.beam_path_set_point, ChangeAxis.POSITION)

    def add_angle_of(self, component):
        """
        Add component which defines the theta angle by it angle; i.e. theta is half the angle of the component - the
            incoming beams angle. This creates an internal list ordered by insertion order. First enabled component is
            used to define theta.
        Args:
            component (ReflectometryServer.components.Component): component that defines theta

        """
        self._beam_path_set_point.add_angle_to(component.beam_path_set_point, ChangeAxis.ANGLE)
        self._beam_path_rbv.add_angle_to(component.beam_path_rbv, component.beam_path_set_point, ChangeAxis.ANGLE)

    def _init_beam_path_calcs(self, setup):
        linear_movement_calc = LinearMovementCalc(setup)

        self._beam_path_set_point = BeamPathCalcThetaSP("{}_sp".format(self.name), linear_movement_calc)
        self._beam_path_rbv = BeamPathCalcThetaRBV("{}_rbv".format(self.name), linear_movement_calc,
                                                   self._beam_path_set_point)


class BenchSetup(PositionAndAngle):
    """
    Setup parameters for the bench component
    """
    def __init__(self, y, z, angle, jack_front_z, jack_rear_z, initial_table_angle, pivot_to_beam,
                 min_angle_for_slide, max_angle_for_slide, vertical_mode=False):
        """
        Initialise.
        Args:
            y: y position of pivot at 0
            z: z position of pivot at 0
            angle: angle that bench pivot moves at
            jack_front_z: distance to the front jack on the bench from the pivot
            jack_rear_z: distance to the rear jack on the bench from the pivot
            initial_table_angle: initial table angle
            pivot_to_beam: distance from the pivot of the bench to the beam
            min_angle_for_slide: minimum angle for moving the horizontal slide; clamp to this angle below
            max_angle_for_slide: maximum angle for moving the horizontal slide; clamp to this angle above
            vertical_mode: True for sample in vertical mode, jacks react to CHI and angle;
                False sample in horixontal mode, jacks move to ANGLE and POSITION
        """
        super(BenchSetup, self).__init__(y, z, angle)
        self.jack_front_z = jack_front_z
        self.jack_rear_z = jack_rear_z
        self.initial_table_angle = initial_table_angle
        self.pivot_to_beam = pivot_to_beam
        self.min_angle_for_slide = min_angle_for_slide
        self.max_angle_for_slide = max_angle_for_slide
        self.vertical_mode = vertical_mode


class BenchComponent(TiltingComponent):
    """
    Bench component, this rotates about a pivot. The pivot can be raised and lowered. Finally the bench can be see sawed
    """

    def __init__(self, name: str, setup: BenchSetup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        self._jack_front_z = setup.jack_front_z
        self._jack_rear_z = setup.jack_rear_z
        self._initial_table_angle = setup.initial_table_angle
        self._pivot_to_beam = setup.pivot_to_beam
        self._min_angle_for_slide = setup.min_angle_for_slide
        self._max_angle_for_slide = setup.max_angle_for_slide
        if setup.vertical_mode:
            self._angle_axis = ChangeAxis.CHI
            self._position_axis = ChangeAxis.HEIGHT
        else:
            self._angle_axis = ChangeAxis.ANGLE
            self._position_axis = ChangeAxis.POSITION
        _, _, self._min_slide_position = self._calculate_motor_positions(0.0, self._min_angle_for_slide, 0.0)
        _, _, self._max_slide_position = self._calculate_motor_positions(0.0, self._max_angle_for_slide, 0.0)
        super(TiltingComponent, self).__init__(name, setup)

    def _init_beam_path_calcs(self, setup):
        """
        Initialise the beam path calcs for the bench.
        Args:
            setup: for bench pivot

        """
        super(BenchComponent, self)._init_beam_path_calcs(setup)

        set_point_axis = self.beam_path_set_point.axis
        set_point_axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)
        rbv_axis = self.beam_path_rbv.axis
        rbv_axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)

        set_point_axis[ChangeAxis.JACK_FRONT] = DirectCalcAxis(ChangeAxis.JACK_FRONT)
        rbv_axis[ChangeAxis.JACK_FRONT] = DirectCalcAxis(ChangeAxis.JACK_FRONT)

        set_point_axis[ChangeAxis.JACK_REAR] = DirectCalcAxis(ChangeAxis.JACK_REAR)
        rbv_axis[ChangeAxis.JACK_REAR] = DirectCalcAxis(ChangeAxis.JACK_REAR)

        set_point_axis[ChangeAxis.SLIDE] = DirectCalcAxis(ChangeAxis.SLIDE)
        rbv_axis[ChangeAxis.SLIDE] = DirectCalcAxis(ChangeAxis.SLIDE)

        self._motor_axes = [ChangeAxis.JACK_FRONT, ChangeAxis.JACK_REAR, ChangeAxis.SLIDE]
        self._control_axes = [self._angle_axis, self._position_axis, ChangeAxis.SEESAW]

        for axis in self._motor_axes:
            set_point_axis[axis].add_listener(AxisChangedUpdate, self.on_motor_axis_changed)
            rbv_axis[axis].add_listener(AxisChangingUpdate, self._is_changing_update)
            rbv_axis[axis].add_listener(PhysicalMoveUpdate, self._on_physical_move)

        for axis in self._control_axes:
            set_point_axis[axis].add_listener(AxisChangedUpdate, self.on_control_axis_changed)
            set_point_axis[axis].add_listener(SetRelativeToBeamUpdate, self.on_set_relative_to_beam)
            rbv_axis[axis].add_listener(DefineValueAsEvent, self.on_define_position)

        set_point_axis[ChangeAxis.JACK_FRONT].add_listener(InitUpdate, self.on_init_update)
        set_point_axis[ChangeAxis.JACK_REAR].add_listener(InitUpdate, self.on_init_update)
        # Slide does not set angles or height so doesn't need an init update listener

    def on_motor_axis_changed(self, update: AxisChangedUpdate):
        """
        If all motor axes have no unapplied changes then set control axes to no-unapplied changes

        """
        if not update.is_changed_update:
            set_point_axes = self.beam_path_set_point.axis
            any_have_unapplied_update = any([set_point_axes[axis].is_changed for axis in self._motor_axes])
            if not any_have_unapplied_update:
                for axis in self._control_axes:
                    set_point_axes[axis].is_changed = False

    def on_control_axis_changed(self, update: AxisChangedUpdate):
        """
        If the current control axis has changes to apply then all motor axes have change to apply
        """
        if update.is_changed_update:
            set_point_axes = self.beam_path_set_point.axis
            for axis in self._motor_axes:
                set_point_axes[axis].is_changed = update.is_changed_update

    def _is_changing_update(self, _):
        """
        If any of the jacks or slide is changing then bench pivot and seesaw are changing
        """
        read_back_axes = self._beam_path_rbv.axis
        is_changing = any([read_back_axes[axis].is_changing for axis in self._motor_axes])
        for axis in self._control_axes:
            read_back_axes[axis].is_changing = is_changing

    def _on_physical_move(self, _):
        """
        When a motor axis moves physically update the control axes
        """
        rbv_axis = self.beam_path_rbv.axis
        height, pivot_angle, seesaw = self._calculate_motor_rbvs(rbv_axis)

        alarm_severity, alarm_status = maximum_severity(rbv_axis[ChangeAxis.JACK_FRONT].alarm,
                                                        rbv_axis[ChangeAxis.JACK_REAR].alarm,
                                                        rbv_axis[ChangeAxis.SLIDE].alarm)

        rbv_axis[self._position_axis].set_displacement(CorrectedReadbackUpdate(height, alarm_severity, alarm_status))
        rbv_axis[self._angle_axis].set_displacement(CorrectedReadbackUpdate(pivot_angle, alarm_severity, alarm_status))
        rbv_axis[ChangeAxis.SEESAW].set_displacement(CorrectedReadbackUpdate(seesaw, alarm_severity, alarm_status))

    def _calculate_motor_rbvs(self, rbv_axis):
        """
        Calculate from the rbv axes the control readback values.
        Args:
            rbv_axis: axis set to use

        Returns:
            height, pivot_angle and seesaw positions
        """
        front_jack = rbv_axis[ChangeAxis.JACK_FRONT].get_displacement()
        rear_jack = rbv_axis[ChangeAxis.JACK_REAR].get_displacement()
        seesaw_sp = self.beam_path_set_point.axis[ChangeAxis.SEESAW].get_displacement()
        if seesaw_sp == 0.0:
            # assume seesaw readback is 0
            height, pivot_angle, seesaw = \
                self._calculate_pivot_height_and_angle_with_fixed_seesaw(front_jack, rear_jack, 0)
        else:
            # assume angle is set correctly and any variation is because of seesaw and height
            angle_sp = self.beam_path_set_point.axis[self._angle_axis].get_displacement()
            height, pivot_angle, seesaw = \
                self._calculate_pivot_height_and_seesaw_with_fixed_pivot_angle(front_jack, rear_jack, angle_sp)
        return height, pivot_angle, seesaw

    def _calculate_pivot_height_and_seesaw_with_fixed_pivot_angle(self, front_jack, rear_jack, pivot_angle):
        """
        Calculate the pivot height and the seesaw value given a fixed pivot angle
        Args:

            front_jack: front jack position
            rear_jack: rear jack position
            pivot_angle: pivot angle

        Returns:
            pivot height, angle and seesaw
        """
        angle_sp_from_initial_position = pivot_angle - self._initial_table_angle
        tan_bench_angle_sp = tan(radians(angle_sp_from_initial_position))
        one_minus_cos_angle_sp = (1 - cos(radians(angle_sp_from_initial_position)))
        height = (front_jack + rear_jack - (self._jack_front_z + self._jack_rear_z) * tan_bench_angle_sp
                  + 2 * self._pivot_to_beam * one_minus_cos_angle_sp) / 2.0
        seesaw = ((self._jack_rear_z - self._jack_front_z) * tan_bench_angle_sp + front_jack - rear_jack) / 2.0
        return height, pivot_angle, seesaw

    def _calculate_pivot_height_and_angle_with_fixed_seesaw(self, front_jack, rear_jack, seesaw):
        """
        Calculate the control values based on the jack if seesaw is fixed at a value
        Args:
            front_jack: front_jack position
            rear_jack: rear jack position
            seesaw: seesaw value

        Returns:
            height, angle and seesaw
        """
        front_jack -= seesaw
        rear_jack += seesaw
        tan_angle_from_initial_position = (front_jack - rear_jack) / (self._jack_front_z - self._jack_rear_z)
        angle_from_initial_position = atan(tan_angle_from_initial_position)
        height = front_jack - self._jack_front_z * tan_angle_from_initial_position + \
            self._pivot_to_beam * (1 - cos(angle_from_initial_position))
        pivot_angle = degrees(angle_from_initial_position) + self._initial_table_angle
        seesaw = 0
        return height, pivot_angle, seesaw

    def on_set_relative_to_beam(self, _):
        """
        When a position is set relative to the beam on the control axes set the transformed values on the motor axes.
        """
        set_point_axes = self.beam_path_set_point.axis
        pivot_height = set_point_axes[self._position_axis].get_displacement()
        pivot_angle = set_point_axes[self._angle_axis].get_displacement()
        seesaw = set_point_axes[ChangeAxis.SEESAW].get_displacement()

        front_jack_height, rear_jack_height, horizontal_position = \
            self._calculate_motor_positions(pivot_height, pivot_angle, seesaw)

        set_point_axes[ChangeAxis.JACK_FRONT].set_relative_to_beam(front_jack_height)
        set_point_axes[ChangeAxis.JACK_REAR].set_relative_to_beam(rear_jack_height)
        set_point_axes[ChangeAxis.SLIDE].set_relative_to_beam(horizontal_position)

    def _calculate_motor_positions(self, pivot_height, pivot_angle, seesaw):
        """
        Give the control axes positions calculate the motor parameters
        Args:
            pivot_height: pivot height
            pivot_angle: pivot angle
            seesaw: seesaw value

        Returns:
            jack front height, jack rear height and horizontal position
        """
        angle_from_initial_position = pivot_angle - self._initial_table_angle
        tan_bench_angle = tan(radians(angle_from_initial_position))
        one_minus_cos_angle = (1 - cos(radians(angle_from_initial_position)))
        # jacks
        height1 = self._jack_front_z * tan_bench_angle
        height2 = self._jack_rear_z * tan_bench_angle
        correction = self._pivot_to_beam * one_minus_cos_angle
        front_jack_height = pivot_height + height1 - correction + seesaw
        rear_jack_height = pivot_height + height2 - correction - seesaw
        # horizontal slide
        if pivot_angle < self._min_angle_for_slide:
            slide_position = self._min_slide_position
        elif pivot_angle <= self._max_angle_for_slide:
            hor = self._jack_rear_z * one_minus_cos_angle
            correction = self._pivot_to_beam * tan_bench_angle
            slide_position = correction - hor
        else:
            slide_position = self._max_slide_position

        return front_jack_height, rear_jack_height, slide_position

    def on_define_position(self, define_position: DefineValueAsEvent):
        """
        When a define position happens on the rbv control parameters take it and apply it to the motor axes after
        transforming the parameters by getting their readback values and setting the newly set parameter.
        Args:
            define_position: the position defined for the axis
        """
        rbv_axis = self.beam_path_rbv.axis
        height, pivot_angle, seesaw = self._calculate_motor_rbvs(rbv_axis)

        change_axis = define_position.change_axis
        if change_axis == self._position_axis:
            height = define_position.new_position

        elif change_axis == self._angle_axis:
            pivot_angle = define_position.new_position

        elif change_axis == ChangeAxis.SEESAW:
            seesaw = define_position.new_position

        else:
            STATUS_MANAGER.update_error_log("Define on bench using axis {} is not allowed".format(change_axis))
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Invalid bench update axis", self.name, Severity.MINOR_ALARM))

        front_jack_height, rear_jack_height, horizontal_position = \
            self._calculate_motor_positions(height, pivot_angle, seesaw)

        rbv_axis[ChangeAxis.JACK_FRONT].define_axis_position_as(front_jack_height)
        rbv_axis[ChangeAxis.JACK_REAR].define_axis_position_as(rear_jack_height)
        if change_axis is not self._position_axis:
            rbv_axis[ChangeAxis.SLIDE].define_axis_position_as(horizontal_position)

    def on_init_update(self, _):
        """
        Jack axis has issued an init update so calculate the pivot height and angle and send an init on those.
        """
        sp_axis = self.beam_path_set_point.axis
        front_jack = sp_axis[ChangeAxis.JACK_FRONT].get_relative_to_beam()
        rear_jack = sp_axis[ChangeAxis.JACK_REAR].get_relative_to_beam()
        seesaw = sp_axis[ChangeAxis.SEESAW].autosaved_value
        if seesaw is None:
            # if autosave is corrupt we must default to 0 (set this on parameter too)
            seesaw = 0
            sp_axis[ChangeAxis.SEESAW].init_displacement_from_motor(seesaw)
        pivot_height, pivot_angle, seesaw = \
            self._calculate_pivot_height_and_angle_with_fixed_seesaw(front_jack, rear_jack, seesaw)

        sp_axis[self._position_axis].init_displacement_from_motor(pivot_height)
        sp_axis[self._angle_axis].init_displacement_from_motor(pivot_angle)
