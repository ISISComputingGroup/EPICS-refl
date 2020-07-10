"""
Components on a beam
"""
from ReflectometryServer.beam_path_calc import TrackingBeamPathCalc, SettableBeamPathCalcWithAngle, \
    BeamPathCalcThetaRBV, BeamPathCalcThetaSP
from ReflectometryServer.axis import DirectCalcAxis, JackCalcAxis, BenchAxisSetup, SlideCalcAxis, AxisChangedUpdate, \
    AxisChangingUpdate
from ReflectometryServer.movement_strategy import LinearMovementCalc
from ReflectometryServer.geometry import ChangeAxis

import logging

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


class BenchComponent(TiltingComponent):
    """
    Bench component, this rotates about a pivot. The pivot can be raised and lowered. Finally the bench can be see sawed
    """

    def __init__(self, name, setup, jack_front_x, jack_rear_x, initial_table_angle, pivot_to_beam):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        self._jack_front_x = jack_front_x
        self._jack_rear_x = jack_rear_x
        self._inital_table_angle = initial_table_angle
        self._pivot_to_beam = pivot_to_beam
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
        bench_axis_setup = BenchAxisSetup(set_point_axis[ChangeAxis.POSITION],
                                          set_point_axis[ChangeAxis.ANGLE],
                                          set_point_axis[ChangeAxis.SEESAW],
                                          self._jack_front_x, self._jack_rear_x,
                                          self._inital_table_angle,
                                          self._pivot_to_beam)
        bench_axis_setup_rbv = BenchAxisSetup(rbv_axis[ChangeAxis.POSITION],
                                              rbv_axis[ChangeAxis.ANGLE],
                                              rbv_axis[ChangeAxis.SEESAW],
                                              self._jack_front_x, self._jack_rear_x,
                                              self._inital_table_angle,
                                              self._pivot_to_beam)

        set_point_axis[ChangeAxis.JACK_FRONT] = JackCalcAxis(ChangeAxis.JACK_FRONT, bench_axis_setup)
        rbv_axis[ChangeAxis.JACK_FRONT] = JackCalcAxis(ChangeAxis.JACK_FRONT, bench_axis_setup_rbv)

        set_point_axis[ChangeAxis.JACK_REAR] = JackCalcAxis(ChangeAxis.JACK_REAR, bench_axis_setup)
        rbv_axis[ChangeAxis.JACK_REAR] = JackCalcAxis(ChangeAxis.JACK_REAR, bench_axis_setup_rbv)

        set_point_axis[ChangeAxis.SLIDE] = SlideCalcAxis(ChangeAxis.SLIDE, bench_axis_setup)
        rbv_axis[ChangeAxis.SLIDE] = SlideCalcAxis(ChangeAxis.SLIDE, bench_axis_setup_rbv)

        self._motor_axes = [ChangeAxis.JACK_FRONT, ChangeAxis.JACK_REAR, ChangeAxis.SLIDE]
        self._control_axes = [ChangeAxis.ANGLE, ChangeAxis.POSITION, ChangeAxis.SEESAW]

        for axis in self._motor_axes:
            set_point_axis[axis].add_listener(AxisChangedUpdate, self.on_motor_axis_changed)
            rbv_axis[axis].add_listener(AxisChangingUpdate, self._is_changing_update)

        for axis in self._control_axes:
            set_point_axis[axis].add_listener(AxisChangedUpdate, self.on_control_axis_changed)

    def on_motor_axis_changed(self, update: AxisChangedUpdate):
        """
        If all motor axes have no unapplied changes then set control axes to no-unapplied changes

        """
        if not update.has_unapplied_update:
            set_point_axes = self.beam_path_set_point.axis
            any_have_unapplied_update = any([set_point_axes[axis].is_changed for axis in self._motor_axes])
            if not any_have_unapplied_update:
                for axis in self._control_axes:
                    set_point_axes[axis].is_changed = False

    def on_control_axis_changed(self, update: AxisChangedUpdate):
        """
        If the current control axis has changes to apply then all motor axes have change to apply
        """
        if update.has_unapplied_update:
            set_point_axes = self.beam_path_set_point.axis
            for axis in self._motor_axes:
                set_point_axes[axis].is_changed = update.has_unapplied_update

    def _is_changing_update(self, _):
        """
        If any of the jacks or slide is changing then bench pivot and seesaw are changing
        """
        read_back_axes = self._beam_path_rbv.axis
        is_changing = any([read_back_axes[axis].is_changing for axis in self._motor_axes])
        for axis in self._control_axes:
            read_back_axes[axis].is_changing = is_changing
