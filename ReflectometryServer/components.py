"""
Components on a beam
"""

from ReflectometryServer.geometry import PositionAndAngle


class Component(object):
    """
    Base object for all components that can sit on a beam line
    """

    def __init__(self, name, movement_strategy):
        """
        Initializer.
        Args:
            name (str): name of the component
            movement_strategy (ReflectometryServer.movement_strategy.LinearMovement): strategy for calculating the
                interception between the movement of the
            component and the incoming beam
        """
        self._rbv_listeners = set()
        self.incoming_beam = None
        self._incoming_beam_for_rbv = None
        self._movement_strategy = movement_strategy
        self.after_beam_path_update_listener = lambda x: None
        self._enabled = True
        self._name = name

    @property
    def enabled(self):
        """
        Returns: the enabled status
        """
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        """
        Updates the component enabled status and notifies the beam path update listener
        Args:
            enabled: The modified enabled status
        """
        self._enabled = enabled
        self.after_beam_path_update_listener(self)

    @property
    def name(self):
        """
        Returns: Name of the component
        """
        return self._name

    def set_incoming_beam(self, incoming_beam):
        """
        Set the incoming beam for the component setpoint calulcation
        Args:
            incoming_beam(PositionAndAngle): incoming beam
        """
        self.incoming_beam = incoming_beam

    def get_outgoing_beam(self):
        """
        Returns the outgoing beam. This class is overiden by components which affect the beam angle.
        Returns (PositionAndAngle): the outgoing beam based on the incoming beam and any interaction with the component
        """
        return self.incoming_beam

    def calculate_beam_interception(self):
        """

        Returns: the position at the point where the components possible movement intercepts the beam

        """
        return self._movement_strategy.calculate_interception(self.incoming_beam)

    def set_position_relative_to_beam(self, displacement):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            displacement: the value to set away from the beam, e.g. height
        """

        self._movement_strategy.set_position_relative_to_beam(self.incoming_beam, displacement)

    def sp_position(self):
        """
        Returns (Position): The set point position of this component.
        """
        return self._movement_strategy.sp_position()

    def add_rbv_relative_to_beam_listener(self, listen_for_value):
        """
        Add a listener for changes in rbv relative to the beam.

        Listeners are called if beam or rbv are set (even if values don't change)
        Args:
            listen_for_value: function

        Returns:

        """
        self._rbv_listeners.add(listen_for_value)

    def set_rbv(self, displacement):
        """

        Args:
            displacement:

        Returns:

        """
        self._movement_strategy.set_rbv(displacement)
        self._calc_rbv_relative_to_beam()

    def _calc_rbv_relative_to_beam(self):
        """
        Perform rbv relative to beam calulations and triggers listeners
        """
        rbv_relative_to_beam = self._movement_strategy.get_rbv_relative_to_beam(self._incoming_beam_for_rbv)
        for listener in self._rbv_listeners:
            listener(rbv_relative_to_beam)

    def set_incoming_beam_for_rbv(self, beam):
        """
        Set the incoming beam for use in the rbv calculation. Also triggers rbv listeners
        Args:
            beam: beam to use
        """
        self._incoming_beam_for_rbv = beam
        self._calc_rbv_relative_to_beam()


class TiltingJaws(Component):
    """
    Jaws which can tilt.
    """
    component_to_beam_angle = 90

    def __init__(self, name, movement_strategy):
        """
        Initializer.
        Args:
            name (str): name of the component
            movement_strategy: strategy encapsulating movement of the component
        """
        super(TiltingJaws, self).__init__(name, movement_strategy)

    def calculate_tilt_angle(self):
        """
        Returns: the angle to tilt so the jaws are perpendicular to the beam.
        """
        return self.get_outgoing_beam().angle + self.component_to_beam_angle


class ReflectingComponent(Component):
    """
    Components which reflects the beam from an reflecting surface at an angle.
    """
    def __init__(self, name, movement_strategy):
        """
        Initializer.
        Args:
            name (str): name of the component
            movement_strategy: strategy encapsulating movement of the component
        """
        super(ReflectingComponent, self).__init__(name, movement_strategy)
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
        self._angle = angle
        self.after_beam_path_update_listener(self)

    def get_outgoing_beam(self):
        """
        Returns: the outgoing beam based on the last set incoming beam and any interaction with the component
        """
        if not self._enabled:
            return self.incoming_beam

        target_position = self.calculate_beam_interception()
        angle_between_beam_and_component = (self._angle - self.incoming_beam.angle)
        angle = angle_between_beam_and_component * 2 + self.incoming_beam.angle
        return PositionAndAngle(target_position.y, target_position.z, angle)

    def set_angle_relative_to_beam(self, angle):
        """
        Set the angle of the component relative to the beamline
        Args:
            angle: angle to set the component at
        """
        self.angle = angle + self.incoming_beam.angle


# class Bench(Component):
#     """
#     Jaws which can tilt.
#     """
#     def __init__(self, name, centre_of_rotation_z, distance_from_sample_to_bench):
#
#         super(Bench, self).__init__(name, ArcMovement(centre_of_rotation_z))
#         self.distance_from_sample_to_bench = distance_from_sample_to_bench
#
#     def calculate_front_position(self):
#         """
#         Returns: the angle to tilt so the jaws are perpendicular to the beam.
#         """
#         center_of_rotation = self.calculate_beam_interception()
#         x = center_of_rotation.z + self.distance_from_sample_to_bench * cos(self.incoming_beam.angle)
#         y = center_of_rotation.y + self.distance_from_sample_to_bench * sin(self.incoming_beam.angle)
#         return Position(y, x)
