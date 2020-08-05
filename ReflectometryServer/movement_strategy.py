"""
Classes and objects describing the movement of items
"""
from __future__ import division

from functools import partial
from math import fabs, tan, radians
from typing import Callable, Optional

from ReflectometryServer.geometry import PositionAndAngle, Position, position_from_radial_coords

# Tolerance to use when comparing an angle with another angle
ANGULAR_TOLERANCE = 1e-12


class LinearMovementCalc:
    """
    A strategy for calculating the interception of the beam with a component that can only move linearly in the Z Y
    plain. E.g. a slit moving vertically to the floor, the position at zero is usually the position of the slit on
    the straight through beam
    """

    def __init__(self, setup: PositionAndAngle,
                 calc_zero_position_and_tilt_fn: Optional[Callable[[PositionAndAngle], PositionAndAngle]] = None):
        """

        Args:
            setup: position in mantid coordinates of the zero point of the axis and its direction of positive travel
            calc_zero_position_and_tilt_fn: function to calculate the position in mantid coordinates of the zero point
                of the axis and its direction of positive travel based on the setup used when
        """
        # Define a function which returns the angle of the axis of travel and the zero position of that axis in mantid
        # coordinates
        if calc_zero_position_and_tilt_fn is None:
            self._get_position_and_angle_of_axis_at_zero = lambda: setup
        else:
            self._get_position_and_angle_of_axis_at_zero = partial(calc_zero_position_and_tilt_fn, setup)
        self._displacement = 0

    def calculate_interception(self, beam):
        """
        Calculate the interception point of the beam and component
        Args:
            beam (PositionAndAngle) : beam to intercept

        Returns (float): position of the interception

        """
        assert beam is not None
        # movement, angle and zero
        m0 = self._get_position_and_angle_of_axis_at_zero()
        angle_m = m0.angle
        # beam angle and zero
        y_b = beam.y
        z_b = beam.z
        angle_b = beam.angle

        if fabs(angle_b % 180.0 - angle_m % 180.0) <= ANGULAR_TOLERANCE:
            raise ValueError("No interception between beam and movement")
        elif fabs(angle_b % 180.0) <= ANGULAR_TOLERANCE:
            y, z = self._zero_angle(y_b, m0, angle_m)
        elif fabs(angle_m % 180.0) <= ANGULAR_TOLERANCE:
            y, z = self._zero_angle(m0.y, beam, beam.angle)
        elif fabs(angle_m % 180.0 - 90) <= ANGULAR_TOLERANCE or fabs(angle_m % 180.0 + 90) <= ANGULAR_TOLERANCE:
            y, z = self._right_angle(m0.z, beam, beam.angle)
        elif fabs(angle_b % 180.0 - 90) <= ANGULAR_TOLERANCE or fabs(angle_b % 180.0 + 90) <= ANGULAR_TOLERANCE:
            y, z = self._right_angle(z_b, m0, angle_m)
        else:
            tan_b = tan(radians(angle_b))
            tan_m = tan(radians(angle_m))
            z = 1 / (tan_m - tan_b) * (y_b - m0.y + m0.z * tan_m - z_b * tan_b)
            y = tan_b * tan_m / (tan_b - tan_m) * (m0.y / tan_m - y_b / tan_b + z_b - m0.z)

        return Position(y, z)

    def _zero_angle(self, y_zero, position, angle):
        """
        Calculate when one of the angles is zero but not the other
        Args:
            y_zero: the y of the item with zero angle
            position: position of other ray
            angle: angle of other ray

        Returns: y and z of intercept

        """
        y = y_zero
        z = position.z + (y_zero - position.y) / tan(radians(angle))
        return y, z

    def _right_angle(self, z_zero, position, angle):
        """
        Calculate when one of the angles is a right angle but not the other
        Args:
            z_zero: the z of the item with right angle
            position: position of other ray
            angle: angle of other ray

        Returns: y and z of intercept
        """

        y = position.y + (z_zero - position.z) * tan(radians(angle))
        z = z_zero
        return y, z

    def _dist_along_axis_from_zero_to_beam_intercept(self, beam):
        """
        Distance along the axis of movement from the zero point to where the beam hits that axis.
        Args:
            beam (PositionAndAngle): the beam ray

        Returns: the distance in the positive sense from the zero point to the intercept with the beam

        """
        beam_intercept = self.calculate_interception(beam)
        position_at_zero = self._get_position_and_angle_of_axis_at_zero()
        diff = position_at_zero - beam_intercept
        dist_to_beam = abs(diff)
        if diff.y > 0:
            direction = -1.0
        else:
            direction = 1.0
        if (position_at_zero.angle % 360.0) >= 180.0:
            direction *= -1
        dist_along_axis_from_zero_to_beam_intercept = dist_to_beam * direction
        return dist_along_axis_from_zero_to_beam_intercept

    def position_in_mantid_coordinates(self, given_displacement=None):
        """
        Returns (Position): The set point position of this component in mantid coordinates.
        """
        displacement = given_displacement
        if displacement is None:
            displacement = self._displacement

        position_at_zero = self._get_position_and_angle_of_axis_at_zero()
        return position_at_zero + position_from_radial_coords(displacement, position_at_zero.angle)

    def set_displacement(self, displacement):
        """
        Set the read back value for the movement. The is the displacement along the axis from the zero point to the
        actual position of the component, in the direction of the axis.
        Args:
            displacement: value along the axis, -ve for before the zero point
        """
        self._displacement = float(displacement)

    def set_distance_relative_to_beam(self, beam, position):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            beam (PositionAndAngle): the current beam ray to set relative to
            position (float): the position relative to the beam that the component should be, e.g. height
        """

        self._displacement = self.get_displacement_relative_to_beam_for(beam, position)

    def get_distance_relative_to_beam(self, beam):
        """
        Given a beam get the distance of the component along the axis of movement from the intercept of the
        beam with the axis of movement.
        Args:
            beam (PositionAndAngle): beam that the rbv is relative to

        Returns (float): distance of the component from the beam along the axis of movement

        """
        return self._displacement - self._dist_along_axis_from_zero_to_beam_intercept(beam)

    def get_distance_relative_to_beam_in_mantid_coordinates(self, incoming_beam):
        """
        Returns (ReflectometryServer.geometry.Position): distance to the beam in mantid coordinates as a vector
        """
        beam_intercept = self.calculate_interception(incoming_beam)
        position = self.position_in_mantid_coordinates()
        return position - beam_intercept

    def get_displacement(self):
        """
        Returns (float): displacement along a axis from the zero position.
        """
        return self._displacement

    def get_displacement_relative_to_beam_for(self, beam, position):
        """
        For a given position this will return the

        Args:
            beam (PositionAndAngle) : the beam ray
            position (float): the position relative to the beam that the component should be, e.g. height

        Returns:
            (float): The sum of the position and distance along axis from 0 to beam intercept
        """
        return position + self._dist_along_axis_from_zero_to_beam_intercept(beam)


# class ArcMovement(PositionAndAngle):
#     """
#     A strategy for calculating the interception of the beam with a component that can only move on a radius
#     """
#
#     def __init__(self, y_center_of_rotation, z_centre_of_rotation):
#         super(ArcMovement, self).__init__(y_center_of_rotation, z_centre_of_rotation, 0)
