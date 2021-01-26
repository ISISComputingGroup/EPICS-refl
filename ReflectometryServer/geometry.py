"""
Objects and classes that handle geometry
"""
from math import radians, sin, cos

from enum import Enum


class Position:
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
            y: y position in room co-ordinates
            z: z position in room co-ordinates
            angle: clockwise angle measured from the horizon (90 to -90 with 0 pointing away from the source)
        """
        super(PositionAndAngle, self).__init__(y, z)
        self.angle = float(angle)

    def __repr__(self):
        return "{}({}, {}, {})".format(self.__class__.__name__, self.y, self.z, self.angle)

    @staticmethod
    def autosave_convert_for_write(value):
        """
        Convert position and angle to a string which can be saved in autosave
        Args:
            value: value to write

        Returns: string representation of the position and angle

        """
        return repr(value)

    @staticmethod
    def autosave_convert_for_read(autosave_read_value):
        """
        Convert a position and angle value from string read in autosave to a position and angle
        Args:
            autosave_read_value: string version of the value

        Returns:
            (PositionAndAngle|None): angle and position or None if conversion can not be done

        """
        try:
            y, z, angle = autosave_read_value[len(PositionAndAngle.__name__)+1:-1].split(",")
            return PositionAndAngle(float(y), float(z), float(angle))
        except (TypeError, ValueError):
            raise ValueError("Converting from string to {}".format(PositionAndAngle.__name__))


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


class ChangeAxis(Enum):
    """
    Types of axes in the component that can change.

    NB Usually POSITION is used instead of HEIGHT and ANGLE instead of PHI so they track the beam.
    """
    POSITION = 0    # tracking position in collimation axis (i.e. height for horizontal samples)
    ANGLE = 1       # tracking angle in plane of collimation
    SEESAW = 2      # Tip of bench
    PHI = 3         # angle like pitch
    CHI = 4         # angle like yaw
    PSI = 5         # angle like roll
    HEIGHT = 6      # height axis perpendicular to beam and the floor
    TRANS = 7       # translation axis perpendicular to beam and parallel to the floor
    LONG_AXIS = 8   # axis along the beam
    JACK_FRONT = 9  # on the bench the jack at the front of the table
    JACK_REAR = 10  # on the bench the jack at the rear of the table
    SLIDE = 11      # on the bench the horizontal slide

