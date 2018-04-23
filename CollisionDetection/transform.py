import numpy as np
from math import sin, cos


class Transformation(object):
    """
    Class that represents a transformation in 3-D space.

    Transformations are represented as 4x4 affine transformation matrices.
    To see more about the maths used in this class, see for example:
    http://www.euclideanspace.com/maths/geometry/affine/matrix4x4/
    """

    def __init__(self, transform=None):
        """
        Initializes a transformation.

        Args:
            transform: the transform to base this transform on. If not supplied, the transform will be initialized
                to the identity transform.
        """
        self.matrix = None

        if transform is None:
            self.identity()
        else:
            self.matrix = transform.matrix

    def identity(self):
        """
        Resets this transformation to the identity transform.
        """
        self.matrix = np.identity(4, dtype=float)

    def rotate(self, rx=0, ry=0, rz=0, forward=True):
        """
        Rotate by the angles rx, ry, rz

        Args:
            rx: the angle to rotate about the x axis
            ry: the angle to rotate about the y axis
            rz: the angle to rotate about the z axis
            forward: If forward is true:   new matrix = rotation . old matrix,
                otherwise it is:      new matrix = old matrix . rotation
                Likewise, this reverses the order of rotation if doing more than one rotation in the same call.
        """

        # Rotation about X
        if rx != 0:
            rotate = np.array([[1., 0., 0., 0.],
                               [0., cos(rx), -sin(rx), 0.],
                               [0., sin(rx), cos(rx), 0.],
                               [0., 0., 0., 1.]])
            if forward:
                self.matrix = np.dot(rotate, self.matrix)
            else:
                self.matrix = np.dot(self.matrix, rotate)

        # Rotation about Y
        if ry != 0:
            rotate = np.array([[cos(ry), 0., -sin(ry), 0.],
                               [0., 1., 0., 0.],
                               [sin(ry), 0., cos(ry), 0.],
                               [0., 0., 0., 1.]])
            if forward:
                self.matrix = np.dot(rotate, self.matrix)
            else:
                self.matrix = np.dot(self.matrix, rotate)

        # Rotation about Z
        if rz != 0:
            rotate = np.array([[cos(rz), -sin(rz), 0., 0.],
                               [sin(rz), cos(rz), 0., 0.],
                               [0., 0., 1., 0.],
                               [0., 0., 0., 1.]])
            if forward:
                self.matrix = np.dot(rotate, self.matrix)
            else:
                self.matrix = np.dot(self.matrix, rotate)

    def translate(self, x=0, y=0, z=0, forward=True):
        """
        Translate by x, y and z

        Args:
            x: the amount to translate the x coordinate by
            y: the amount to translate the y coordinate by
            z: the amount to translate the z coordinate by
            forward: If forward is true:   new matrix = translation . old matrix,
                    otherwise it is:      new matrix = old matrix . translation
        """
        if forward:
            self.matrix = np.dot(
                np.array([[1., 0., 0., x],
                          [0., 1., 0., y],
                          [0., 0., 1., z],
                          [0., 0., 0., 1.]]), self.matrix)
        else:
            self.matrix = np.dot(self.matrix,
                                 np.array([[1., 0., 0., x],
                                           [0., 1., 0., y],
                                           [0., 0., 1., z],
                                           [0., 0., 0., 1.]]))

    def scale(self, x=1, y=1, z=1):
        """
        Scales in x, y and z

        Args:
            x: The scale factor for the x axis
            y: The scale factor for the y axis
            z: The scale factor for the z axis
        """
        self.matrix = np.dot(np.diagflat([x, y, z, 1]), self.matrix)

    def evaluate(self, position):
        """
        Given a set of [x, y ,z] coordinates, calculate transformed position.

        Args:
            position: collection of 3 items [x, y, z], which correspond to a point in 3D space to be transformed.

        Returns:
            a collection of 3 items [x, y, z] which are the result of applying the transformation to the position.
        """
        assert len(position) == 3
        x, y, z = position

        # To transform a point using an affine transformation matrix, pass [x, y, z, 1] as the position vector and take
        # the dot product. The first 3 elements of the resulting vector are the new position.
        return np.dot(self.matrix, [x, y, z, 1.0])[0:3]

    def get_position_matrix(self):
        """
        Gets the position vector from this transform.

        Returns:
            A 1x3 numpy matrix corresponding to the position of this transform.
        """
        return np.reshape(self.matrix[0:3, 3], (1, 3))

    def get_rotation_matrix(self):
        """
        Gets the rotation matrix from this transform.

        Returns:
            A 3x3 numpy matrix corresponding to the rotation of this transform.
        """
        return np.reshape(self.matrix[0:3, 0:3], (3, 3))

    def join(self, rotation, position):
        """
        Join matrix from rotation and position matrices.

        Args:
            rotation: a collection of 9 items corresponding to a rotation matrix.
            position: a collection of 3 items corresponding to a position 3-vector

        Returns:
            A transformation matrix built from the rotation and positions provided.
        """
        assert len(position) == 3
        assert len(rotation) == 9

        r = rotation
        p = position

        self.matrix = np.array([[r[0], r[1], r[2], p[0]],
                                [r[3], r[4], r[5], p[1]],
                                [r[6], r[7], r[8], p[2]],
                                [0., 0., 0., 1.]])

        return self.matrix

    def get_inverse(self):
        """
        Gets the inverse of this transformation (the transformation with opposite effect).

        Returns:
            A Transformation object with opposite effect.
        """
        inverse_transform = Transformation()
        inverse_transform.matrix = np.linalg.inv(self.matrix)
        return inverse_transform

    def __str__(self):
        return str(self.matrix)
