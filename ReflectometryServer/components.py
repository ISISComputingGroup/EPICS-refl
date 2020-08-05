"""
Components on a beam
"""
from typing import Optional

from ReflectometryServer.beam_path_calc import TrackingBeamPathCalc, SettableBeamPathCalcWithAngle, \
    BeamPathCalcThetaRBV, BeamPathCalcThetaSP, DirectCalcAxis
from ReflectometryServer.movement_strategy import LinearMovementCalc
from ReflectometryServer.geometry import ChangeAxis, PositionAndAngle

import logging

logger = logging.getLogger(__name__)


class Component:
    """
    Base object for all components that can sit on a beam line
    """

    def __init__(self, name: str, setup: PositionAndAngle, on: Optional['Component'] = None):
        """
        Initializer.
        Args:
            name: name of the component
            setup: initial setup for the component
            on: the component on which this component is mounted, component then moves with underlying component;
                None for not on another component
        """
        self._name = name
        self._on_component = on
        if self._on_component is None:
            on_beam_path_sp = None
            on_beam_path_rbv = None
        else:
            on_beam_path_sp = self._on_component.beam_path_set_point.mantid_position_at
            on_beam_path_rbv = self._on_component.beam_path_rbv.mantid_position_at
        self._init_beam_path_calcs(setup, on_beam_path_sp, on_beam_path_rbv)
        for axis_to_add in [ChangeAxis.PHI, ChangeAxis.CHI, ChangeAxis.PSI, ChangeAxis.TRANS, ChangeAxis.HEIGHT]:
            self._beam_path_set_point.axis[axis_to_add] = DirectCalcAxis(axis_to_add)
            self._beam_path_rbv.axis[axis_to_add] = DirectCalcAxis(axis_to_add)

    def __repr__(self):
        return "{}({} beampath sp:{!r}, beampath rbv:{!r})), ".format(
            self.__class__.__name__, self._name, self._beam_path_set_point, self._beam_path_rbv)

    def _init_beam_path_calcs(self, setup, on_beam_path_sp, on_beam_path_rbv):
        self._beam_path_set_point = TrackingBeamPathCalc("{}_sp".format(self.name),
                                                         LinearMovementCalc(setup, on_beam_path_sp))
        self._beam_path_rbv = TrackingBeamPathCalc("{}_rbv".format(self.name),
                                                   LinearMovementCalc(setup, on_beam_path_rbv))

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

    def _init_beam_path_calcs(self, setup, on_beam_path_sp, on_beam_path_rbv):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name),
                                                                  LinearMovementCalc(setup, on_beam_path_sp),
                                                                  is_reflecting=False)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name),
                                                            LinearMovementCalc(setup, on_beam_path_rbv),
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

    def _init_beam_path_calcs(self, setup, on_beam_path_sp, on_beam_path_rbv):
        self._beam_path_set_point = SettableBeamPathCalcWithAngle("{}_sp".format(self.name),
                                                                  LinearMovementCalc(setup, on_beam_path_sp),
                                                                  is_reflecting=True)
        self._beam_path_rbv = SettableBeamPathCalcWithAngle("{}_rbv".format(self.name),
                                                            LinearMovementCalc(setup, on_beam_path_rbv),
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

    def _init_beam_path_calcs(self, setup, on_beam_path_sp, on_beam_path_rbv):
        self._beam_path_set_point = BeamPathCalcThetaSP("{}_sp".format(self.name),
                                                        LinearMovementCalc(setup, on_beam_path_sp))
        self._beam_path_rbv = BeamPathCalcThetaRBV("{}_rbv".format(self.name),
                                                   LinearMovementCalc(setup, on_beam_path_rbv),
                                                   self._beam_path_set_point)


class BenchComponent(TiltingComponent):
    """
    Bench component, this rotates about a pivot. The pivot can be raised and lowered. Finally the bench can be see sawed
    """

    def __init__(self, name, setup):
        """
        Initializer.
        Args:
            name (str): name of the component
            setup (ReflectometryServer.geometry.PositionAndAngle): initial setup for the component
        """
        super(TiltingComponent, self).__init__(name, setup)

    def _init_beam_path_calcs(self, setup, on_beam_path_sp, on_beam_path_rbv):
        super(BenchComponent, self)._init_beam_path_calcs(setup, on_beam_path_sp, on_beam_path_rbv)

        self.beam_path_set_point.axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)
        self.beam_path_rbv.axis[ChangeAxis.SEESAW] = DirectCalcAxis(ChangeAxis.SEESAW)
