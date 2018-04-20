import unittest
import numpy as np
from CollisionDetection.transform import Transformation


class TransformTests(unittest.TestCase):

    def test_GIVEN_new_transform_THEN_it_is_the_identity_matrix(self):
        identity_matrix = np.identity(4)

        self.assertTrue(np.array_equal(Transformation().matrix, identity_matrix))

    def test_GIVEN_translation_matrix_THEN_it_is_a_correct_translation(self):

        x, y, z = 2, 3, 4

        t = Transformation()
        t.translate(x, y, z)

        expected_matrix = np.array([[1, 0, 0, x],
                                    [0, 1, 0, y],
                                    [0, 0, 1, z],
                                    [0, 0, 0, 1]])

        self.assertTrue(np.array_equal(t.matrix, expected_matrix))

    def test_GIVEN_input_matrix_WHEN_finding_inverse_THEN_result_is_expected_inverse(self):
        test_matrix = np.array([[1, 2, 3, 4],
                                [0, 6, 7, 8],
                                [0, 0, 7, 8],
                                [0, 0, 0, 1]])

        t = Transformation()
        t.matrix = test_matrix

        self.assertTrue(np.array_equal(np.linalg.inv(test_matrix), t.get_inverse()))
