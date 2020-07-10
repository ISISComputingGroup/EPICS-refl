"""
Components on a beam
"""
from ReflectometryServer.beam_path_calc import TrackingBeamPathCalc, SettableBeamPathCalcWithAngle, \
    BeamPathCalcThetaRBV, BeamPathCalcThetaSP
from ReflectometryServer.axis import DirectCalcAxis, JackCalcAxis, BenchAxisSetup, SlideCalcAxis
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

        self.beam_path_set_point.axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)
        self.beam_path_rbv.axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)
        bench_axis_setup = BenchAxisSetup(self.beam_path_set_point.axis[ChangeAxis.POSITION],
                                          self.beam_path_set_point.axis[ChangeAxis.ANGLE],
                                          self.beam_path_set_point.axis[ChangeAxis.SEESAW],
                                          self._jack_front_x, self._jack_rear_x,
                                          self._inital_table_angle,
                                          self._pivot_to_beam, self._is_changed_update)
        bench_axis_setup_rbv = BenchAxisSetup(self.beam_path_rbv.axis[ChangeAxis.POSITION],
                                              self.beam_path_rbv.axis[ChangeAxis.ANGLE],
                                              self.beam_path_rbv.axis[ChangeAxis.SEESAW],
                                              self._jack_front_x, self._jack_rear_x,
                                              self._inital_table_angle,
                                              self._pivot_to_beam, self._is_changed_update)

        self.beam_path_set_point.axis[ChangeAxis.JACK_FRONT] = JackCalcAxis(ChangeAxis.JACK_FRONT, bench_axis_setup)
        self.beam_path_rbv.axis[ChangeAxis.JACK_FRONT] = JackCalcAxis(ChangeAxis.JACK_FRONT, bench_axis_setup_rbv)

        self.beam_path_set_point.axis[ChangeAxis.JACK_REAR] = JackCalcAxis(ChangeAxis.JACK_REAR, bench_axis_setup)
        self.beam_path_rbv.axis[ChangeAxis.JACK_REAR] = JackCalcAxis(ChangeAxis.JACK_REAR, bench_axis_setup_rbv)

        self.beam_path_set_point.axis[ChangeAxis.SLIDE] = SlideCalcAxis(ChangeAxis.SLIDE, bench_axis_setup)
        self.beam_path_rbv.axis[ChangeAxis.SLIDE] = SlideCalcAxis(ChangeAxis.SLIDE, bench_axis_setup_rbv)

    def _is_changed_update(self):
        """
        Update the changed property on bench pivot and seesaw control axis based on jacks and slide changed. If one
        of jacks or slide is_changed then all bench pivot and seesaw axes are changed.

        """
        is_changed = self.beam_path_set_point.axis[ChangeAxis.JACK_FRONT].only_this_axis_is_changed() or \
            self.beam_path_set_point.axis[ChangeAxis.JACK_REAR].only_this_axis_is_changed() or \
            self.beam_path_set_point.axis[ChangeAxis.SLIDE].only_this_axis_is_changed()
        self._beam_path_set_point.axis[ChangeAxis.POSITION].is_changed = is_changed
        self._beam_path_set_point.axis[ChangeAxis.ANGLE].is_changed = is_changed
        self._beam_path_set_point.axis[ChangeAxis.SEESAW].is_changed = is_changed
