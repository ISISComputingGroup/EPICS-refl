"""
Objects and classes that handle geometry
"""
from math import radians, sin, cos


class Position(object):
    """
    The beam position and direction
    """
    def __init__(self, y, z):
        self.z = float(z)
        self.y = float(y)

    def __add__(self, other):
        return Position(self.y + other.y, self.z + other.z)

    def __repr__(self):
        return "Position(x, {}, {})".format(self.y, self.z)


class PositionAndAngle(Position):
    """
    The beam position and direction
    """
    def __init__(self, y, z, angle):
        """

        Args:
            z: z position in room co-ordinates
            y: y position in room co-ordinates
            angle: clockwise angle measured from the horizon (90 to -90 with 0 pointing away from the source)
        """
        super(PositionAndAngle, self).__init__(y, z)
        self.angle = float(angle)

    def __repr__(self):
        return "PositionAndAngle({}, {}, {})".format(self.z, self.y, self.angle)


def position_from_radial_coords(r, theta, angle=None):
    """
    Create a position based on radial coordinates. If angle included create a position and angle.
    Args:
        r: radius
        theta: angle of the point position
        angle: clockwise angle measured from the horizon (90 to -90 with 0 pointing away from the source); if None
            return just position

    Returns (Position): position object
    """
    x = r * sin(radians(theta))
    y = r * cos(radians(theta))
    if angle is None:
        return Position(x, y)
    else:
        return PositionAndAngle(x, y, angle)
