import numpy as np
import ode

from transform import Transformation

class GeometryBox(object):
    def __init__(self, space, position=(0, 0, 0), size=(1, 1, 1), color=(1, 1, 1), oversize=1, name=None):

        # Set parameters for drawing the body
        self.color = color
        self.size = list(size)
        self.oversize = oversize

        # Create a box geom for collision detection
        self.geom = ode.GeomBox(space, lengths=[s + 2 + oversize for s in self.size])
        self.geom.setPosition(position)

        # A friendly name
        self.name = name

    # Set the size of the ODE geometry
    def set_size(self, x=None, y=None, z=None, oversize=None):
        # Only need to set the size of dimensions supplied
        if x is not None:
            self.size[0] = x
        if y is not None:
            self.size[1] = y
        if z is not None:
            self.size[2] = z
        if oversize is not None:
            self.oversize = oversize
        self.geom.setLengths([s + 2 * self.oversize for s in self.size])

    # Set the transform for the geometry
    def set_transform(self, transform):
        # Get the rotation and position elements from the transformation matrix
        rot, pos = transform.split()

        # Reshape the rotation matrix into a ODE friendly format
        rot = np.reshape(rot, 9)

        # Apply the translation and rotation to the ODE geometry
        self.geom.setPosition(pos)
        self.geom.setRotation(rot)

    def get_transform(self):
        t = Transformation()
        t.join(self.geom.getRotation(), self.geom.getPosition())
        return t

    def get_vertices(self):
        vertices = np.array([(-0.5, -0.5, 0.5),
                             (0.5, -0.5, 0.5),
                             (0.5, 0.5, 0.5),
                             (-0.5, 0.5, 0.5),
                             (-0.5, -0.5, -0.5),
                             (0.5, -0.5, -0.5),
                             (0.5, 0.5, -0.5),
                             (-0.5, 0.5, -0.5)])

        vertices *= self.geom.getLengths()

        t = self.get_transform()

        vertices = [t.evaluate(v) for v in vertices]

        return vertices