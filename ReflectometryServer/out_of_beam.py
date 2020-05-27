class OutOfBeamPosition:
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


class OutOfBeamLookup:
    """
    Facilitates lookup of out-of-beam positions / status for a single axis out of a list of possible positions depending
    on where the beam intersects with that movement axis.
    """
    def __init__(self, positions):
        self._validate(positions)
        self._sorted_out_of_beam_positions = sorted(positions, key=lambda position: (
        position.threshold is None, position.threshold), reverse=True)

    @staticmethod
    def _validate(positions):
        """
        Validate the given list of positions for this looukup.

        Args:
            positions (list[OutOfBeamPositions]: The positions
        """
        if positions:
            filter_default = [x for x in positions if x.threshold is None]
            if len(filter_default) == 0:
                raise ValueError("ERROR: No default Out Of Beam Position defined for lookup.")
            if len(filter_default) > 1:
                raise ValueError("ERROR: Multiple default Out Of Beam Position defined for lookup.")
            thresholds = [entry.threshold for entry in positions]
            if len(set(thresholds)) != len(thresholds):
                raise ValueError("ERROR: Duplicate values for threshold in different Out Of Beam positions.")
        else:
            raise ValueError("ERROR: No positions defined.")

    def get_position_for_intercept(self, beam_intercept):
        """
        Returns the appropriate out-of-beam position along the movement axis for the given beam interception.

        Args:
            beam_intercept (ReflectometryServer.geometry.Position): The beam interception for the movement axis
                with out-of-beam positions

        Returns: The out-of-beam position
        """
        default_pos = self._sorted_out_of_beam_positions[0]
        pos_with_threshold_below_intercept = [x for x in self._sorted_out_of_beam_positions[1:] if
                                              x.threshold <= beam_intercept.y]
        if len(pos_with_threshold_below_intercept) > 0:
            position_to_use = pos_with_threshold_below_intercept[0]
        else:
            position_to_use = default_pos
        return position_to_use

    def is_in_beam(self, beam_intercept, displacement):
        """
        Checks whether a given value for displacement represents an out of beam position for a given beam interception.

        Args:
            beam_intercept(ReflectometryServer.geometry.Position): The current beam interception
            displacement(float): The value to search in out of beam positions.

        Returns: False if the given displacement represents an out of beam position, True otherwise
        """
        out_of_beam_position = self.get_position_for_intercept(beam_intercept)
        return abs(displacement - out_of_beam_position.position) > out_of_beam_position.tolerance
