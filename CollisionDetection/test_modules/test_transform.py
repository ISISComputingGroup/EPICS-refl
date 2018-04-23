import unittest
import numpy as np
from CollisionDetection.transform import Transformation


class TransformTests(unittest.TestCase):

    def test_GIVEN_new_transform_THEN_it_is_the_identity_matrix(self):
        identity_matrix = np.identity(4)

        self.assertTrue(np.array_equal(Transformation().matrix, identity_matrix))

    def test_GIVEN_a_blank_transform_WHEN_applied_to_a_set_of_points_THEN_transform_has_no_effect(self):

        test_position = [5, 6, 7]

        t = Transformation()
        evaluated_position = t.evaluate(test_position)

        self.assertTrue(np.array_equal(evaluated_position, test_position))

    def test_GIVEN_translation_transform_WHEN_applied_to_a_vector_THEN_vector_is_translated(self):

        original_x, original_y, original_z = 5, 6, 7
        translation_x, translation_y, translation_z = 2, 3, 4

        t = Transformation()
        t.translate(translation_x, translation_y, translation_z)

        evaluated_position = t.evaluate([original_x, original_y, original_z])

        self.assertTrue(np.array_equal(evaluated_position, [
            original_x + translation_x,
            original_y + translation_y,
            original_z + translation_z,
        ]))

    def test_GIVEN_scale_transform_WHEN_applied_to_a_vector_THEN_vector_is_scaled(self):

        original_x, original_y, original_z = 5, 6, 7
        scale_x, scale_y, scale_z = 2, 3, 4

        t = Transformation()
        t.scale(scale_x, scale_y, scale_z)

        evaluated_position = t.evaluate([original_x, original_y, original_z])

        self.assertTrue(np.array_equal(evaluated_position, [
            original_x * scale_x,
            original_y * scale_y,
            original_z * scale_z,
        ]))

    def test_GIVEN_transformation_WHEN_applying_transformation_and_then_inverse_THEN_original_position_recovered(self):
        test_position = [5, 6, 7]

        # Build up a transformation. Numbers here are not important - but should probably use all of the major
        # operations (translate/rotate/scale etc).
        t = Transformation()
        t.rotate(50, 70, 90)
        t.scale(4, 5, 6)
        t.translate(7, 8, 9)

        transformed_position = t.evaluate(test_position)

        inverse_transform = t.get_inverse()

        # Sanity check that our transform did something.
        self.assertFalse(np.array_equal(test_position, transformed_position))

        # Check that applying the inverse successfully undoes the original transformation.
        self.assertTrue(np.array_equal(test_position, inverse_transform.evaluate(transformed_position)))
