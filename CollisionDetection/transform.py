import numpy as np
from math import sin, cos


class Transformation(object):
    # Initialise the transformation matrix to an identity
    def __init__(self, transform=None):
        self.matrix = None

        if transform is None:
            self.identity()
        else:
            self.matrix = transform.matrix

    # Reset the matrix to an identity - clears all transforms
    def identity(self):
        self.matrix = np.identity(4, dtype=float)

    def rotate(self, rx=0, ry=0, rz=0, forward=True):
        """
        Rotate by the angles rx, ry, rz

        If forward is true:   new matrix = rotation . old matrix,
        otherwise it is:      new matrix = old matrix . rotation
        Likewise, this reverses the order of rotation if doing more than one rotation in the same call
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

        If forward is true:   new matrix = translation . old matrix,
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
        """
        self.matrix = np.dot(np.diagflat([x, y, z, 1]), self.matrix)

    def evaluate(self, position):
        """
        Given a set of [x, y ,z] coordinates, calculate transformed position
        """
        assert len(position) == 3
        x, y, z = position
        position = [x, y, z, 1.0]

        result = np.dot(self.matrix, position)

        return result[0:3]

    def split(self):
        """
        Separate matrix into rotation and position matrices
        """
        rotation = self.matrix[0:3, 0:3]
        position = self.matrix[0:3, 3]

        return rotation, position

    def join(self, rotation, position):
        """
        Join matrix from rotation and position matrices
        """
        assert len(position) == 3
        assert len(rotation) == 9

        r = rotation
        p = position

        self.matrix = np.array([[r[0], r[1], r[2], p[0]],
                                [r[3], r[4], r[5], p[1]],
                                [r[6], r[7], r[8], p[2]],
                                [0.00, 0.00, 0.00, 1.00]])

        return self.matrix

    def get_inverse(self):
        """
        Gets the inverse of this transformation (the matrix with opposite effect).
        :return: The inverted matrix
        """
        return np.linalg.inv(self.matrix)

    def __str__(self):
        return str(self.matrix)
