"""
Objects and classes that handle geometry
"""


class Position(object):
    """
    The beam position and direction
    """
    def __init__(self, y, z):
        self.z = float(z)
        self.y = float(y)

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
