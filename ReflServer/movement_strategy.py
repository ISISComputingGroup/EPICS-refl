"""
Classes and objects decribing the movement of items
"""

from math import fabs, tan, radians, sin, cos

from ReflServer.gemoetry import PositionAndAngle, Position

# Tolerance to use when comparing an angle with another angle
ANGULAR_TOLERANCE = 1e-12


class LinearMovement(object):
    """
    A strategy for calculating the interception of the beam with a component that can only move linearly in the Z Y
    plain. E.g. a slit moving vertically to the floor
    """

    def __init__(self, y_position, z_position, angle):
        self._angle_and_position = PositionAndAngle(y_position, z_position, angle)

    def calculate_interception(self, beam):
        """
        Calculate the interception point of the beam and component
        Args:
            beam(PositionAndAngle) : beam to intercept

        Returns: position of the interception

        """
        assert beam is not None
        y_m = self._angle_and_position.y
        z_m = self._angle_and_position.z
        angle_m = self._angle_and_position.angle
        y_b = beam.y
        z_b = beam.z
        angle_b = beam.angle

        if fabs(angle_b % 180.0 - angle_m % 180.0) <= ANGULAR_TOLERANCE:
            raise ValueError("No interception between beam and movement")
        elif fabs(angle_b % 180.0) <= ANGULAR_TOLERANCE:
            y, z = self._zero_angle(y_b, self._angle_and_position)
        elif fabs(angle_m % 180.0) <= ANGULAR_TOLERANCE:
            y, z = self._zero_angle(y_m, beam)
        elif fabs(angle_m % 180.0 - 90) <= ANGULAR_TOLERANCE or fabs(angle_m % 180.0 + 90) <= ANGULAR_TOLERANCE:
            y, z = self._right_angle(z_m, beam)
        elif fabs(angle_b % 180.0 - 90) <= ANGULAR_TOLERANCE or fabs(angle_b % 180.0 + 90) <= ANGULAR_TOLERANCE:
            y, z = self._right_angle(z_b, self._angle_and_position)
        else:
            tan_b = tan(radians(angle_b))
            tan_m = tan(radians(angle_m))
            z = 1/(tan_m - tan_b) * (y_b - y_m + z_m * tan_m - z_b * tan_b)
            y = tan_b * tan_m / (tan_b - tan_m) * (y_m / tan_m - y_b / tan_b + z_b - z_m)

        return Position(y, z)

    def _zero_angle(self, y_zero, position_and_angle):
        """
        Calculate when one of the angles is zero but not the other
        Args:
            y_zero: the y of the item with zero angle
            position_and_angle: position and angle of other ray

        Returns: y and z of intercept

        """
        y = y_zero
        z = position_and_angle.z + (y_zero - position_and_angle.y) / tan(radians(position_and_angle.angle))
        return y, z

    def _right_angle(self, z_zero, position_and_angle):
        """
        Calculate when one of the angles is a right angle but not the other
        Args:
            z_zero: the z of the item with right angle
            position_and_angle: position and angle of other ray

        Returns: y and z of intercept
        """

        y = position_and_angle.y + (z_zero - position_and_angle.z) * tan(radians(position_and_angle.angle))
        z = z_zero
        return y, z

    def set_position_relative_to_beam(self, beam_intercept, value):
        """
        Set the position of the component relative to the beam for the given value based on its movement strategy.
        For instance this could set the height above the beam for a vertically moving component
        Args:
            beam_intercept: the current beam position of the item
            value: the value to set away from the beam, e.g. height
        """
        angle = self._angle_and_position.angle
        y_value = beam_intercept.y + value * sin(radians(angle))
        z_value = beam_intercept.z + value * cos(radians(angle))

        self._angle_and_position = PositionAndAngle(y_value, z_value, angle)

    def sp_position(self):
        """
        Returns (Position): The set point position of this component.
        """
        return Position(self._angle_and_position.y, self._angle_and_position.z)


# class ArcMovement(LinearMovement):
#     """
#     A strategy for calculating the interception of the beam with a component that can only move on a radius
#     """
#
#     def __init__(self, y_center_of_rotation, z_centre_of_rotation):
#         super(ArcMovement, self).__init__(y_center_of_rotation, z_centre_of_rotation, 0)
