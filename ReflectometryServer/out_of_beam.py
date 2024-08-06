"""
Module to define Out of beam position.
"""
from typing import List, Optional, Tuple

from ReflectometryServer.geometry import Position


class OutOfBeamPosition:
    """
    The definition of a geometry component's out of beam position.
    """
    def __init__(self, position, tolerance: float = 1, threshold: Optional[float] = None, is_offset: bool = False):
        """
        Params:
            position: The out-of-beam position along the movement axis.
            tolerance: The tolerance around the position in which to consider the component as "out of beam"
            threshold: The threshold for the beam above which to consider this position to be "out of beam"
            is_offset: Turns the position into an offset so that the parked position follows the beam with the offset
                set added to it.
        """
        self._final_position = float(position)
        self.tolerance = float(tolerance)
        if threshold is not None:
            threshold = float(threshold)
        self.threshold = threshold
        self.is_offset = is_offset
        self._sequence = [position]

    def get_final_position(self) -> float:
        """

        Returns: final position out of beam position after any parking sequence has been executed

        """
        return self._final_position

    def get_sequence_position(self, parking_index):
        """
        Get the position at the current parking sequence. If past the end of the sequence return the final position
        Args:

            parking_index: parking sequence number; None for finally parking position

        Returns:
            parking position for index; None there is no sequence position for this index
        """
        if parking_index is None or len(self._sequence) <= parking_index:
            return None
        return self._sequence[parking_index]

    def get_parking_sequence_length(self):
        """
        Returns: length of the parking sequence
        """
        return len(self._sequence)


class OutOfBeamLookup:
    """
    Facilitates lookup of out-of-beam positions / status for a single axis out of a list of possible positions depending
    on where the beam intersects with that movement axis.
    """
    def __init__(self, positions: List[OutOfBeamPosition]):
        self._validate(positions)
        self._sorted_out_of_beam_positions = sorted(positions, key=lambda position:
                                                    (position.threshold is None, position.threshold), reverse=True)

    @staticmethod
    def _validate(positions):
        """
        Validate the given list of positions for this lookup.

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

    def get_position_for_intercept(self, beam_intercept: Position):
        """
        Returns the appropriate out-of-beam position along the movement axis for the given beam interception.

        Args:
            beam_intercept: The beam interception for the movement axis
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

    def out_of_beam_status(self, beam_intercept: Position, displacement: float, distance_from_beam: float,
                           parking_index: Optional[int]) -> Tuple[bool, bool]:
        """
        Checks whether a given value for displacement represents an out of beam position or at the end of the current
            sequence for a given beam interception and parking sequence number.

        Args:
            beam_intercept: The current beam interception
            displacement: The value to search in out of beam positions.
            distance_from_beam: Distance from the beam to the current position
            parking_index: current parking sequence index

        Returns:
            False if the given displacement represents an out of beam position, True otherwise
            True if the given displacement is at the end of the current sequence number, False otherwise;
                if parking sequence is None then return True we are at the end of the sequence because we are not
                waiting to finish movement; If we are after the last parking sequence also return True because we must
                have reached the last position
        """
        out_of_beam_position = self.get_position_for_intercept(beam_intercept)
        if out_of_beam_position.is_offset:
            axis_position = distance_from_beam
        else:
            axis_position = displacement
        in_beam = abs(axis_position - out_of_beam_position.get_final_position()) > out_of_beam_position.tolerance
        is_at_sequence_position = out_of_beam_position.get_sequence_position(parking_index)
        if is_at_sequence_position is None:
            at_sequence_index = True
        else:
            at_sequence_index = abs(axis_position - is_at_sequence_position) < out_of_beam_position.tolerance

        return in_beam, at_sequence_index

    def get_max_sequence_count(self):
        """

        Returns: maximum sequence length for any parking sequence

        """
        return max([position.get_parking_sequence_length() for position in self._sorted_out_of_beam_positions])


class OutOfBeamSequence(OutOfBeamPosition):
    """
    Out of Beam position which gives a sequence instead of just a fixed position.
    """

    def __init__(self, sequence, tolerance: float = 1, threshold: Optional[float] = None, is_offset: bool = False):
        """
        Initialise.
        Args:
            sequence: sequence of park positions that the component will go through when parking the axis. None is don't
                move it; if the sequence is too short last value is repeated
            tolerance: tolerance to within which the axis must get before the sequence number is increased or for final
                point that the axis is assumed to be out of beam
            threshold: The threshold for the beam above which to consider this position to be "out of beam"
            is_offset: Turns the position into an offset so that the parked position follows the beam with the offset
                set added to it.
        """
        self._validate(sequence)
        super(OutOfBeamSequence, self).__init__(sequence[-1], tolerance, threshold, is_offset)
        self._sequence = sequence

    def _validate(self, sequence):
        if sequence[-1] is None:
            raise ValueError("ERROR: Out of beam sequence ends in None this is not allowed")

        found_non_none = False
        for val in sequence:
            if val is None and found_non_none:
                raise ValueError("ERROR: Out of beam sequence has a None between values this is not allowed")
            elif val is not None:
                found_non_none = True
