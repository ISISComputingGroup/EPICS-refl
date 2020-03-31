from collections import namedtuple


class OutOfBeamPosition(object):
    """
    The definition of a geometry component's out of beam position.
    """
    def __init__(self, position, tolerance=1, threshold=None):
        """
        Params:
            position(float): The out-of-beam position along the movement axis.
            tolerance(float): The tolerance around the position in which to consider the component as "out of beam"
            threshold(float): The threshold for the beam above which to consider this position to be "out of beam"
        """
        self.position = float(position)
        self.tolerance = float(tolerance)
        if threshold is not None:
            threshold = float(threshold)
        self.threshold = threshold


class OutOfBeamLookup(object):
    def __init__(self, positions):
        self._validate(positions)
        self._out_of_beam_positions = positions

    def _validate(self, positions):
        # TODO raise something, catch in component
        if positions:
            filter_default = filter(lambda x: x.threshold is None, positions)
            if len(filter_default) == 0:
                raise ValueError("ERROR: No default Out Of Beam Position defined for lookup.")
            if len(filter_default) > 1:
                raise ValueError("ERROR: Multiple default Out Of Beam Position defined for lookup.")
            thresholds = [entry.threshold for entry in positions]
            if len(set(thresholds)) != len(thresholds):
                raise ValueError("ERROR: Duplicate values for threshold in different Out Of Beam positions.")

    def get_position_for_intercept(self, beam_intercept):
        pos_above_threshold = filter(lambda x: x.threshold <= beam_intercept.y, self._out_of_beam_positions)
        return sorted(pos_above_threshold, key=lambda position: position.threshold, reverse=True)[0]

    def is_in_beam(self, beam_intercept, displacement):
        """
        Checks whether a given value for displacement represents an out of beam position for a given beam interception.

        Args:
            beam_intercept(ReflectometryServer.geometry.Position): The current beam interception
            displacement(float): The value to search in out of beam positions.

        Returns: False if the given displacement represents an out of beam position, True otherwise
        """
        if not self._out_of_beam_positions:
            return True

        out_of_beam_position = self.get_position_for_intercept(beam_intercept)
        return abs(displacement - out_of_beam_position.position) > out_of_beam_position.tolerance
