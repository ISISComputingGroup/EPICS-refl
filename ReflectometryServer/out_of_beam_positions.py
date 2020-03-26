from collections import namedtuple

OutOfBeamPosition = namedtuple("OutOfBeamPosition", [
    "threshold",
    "position",
    "tolerance"])


class OutOfBeamLookup(object):
    def __init__(self, positions):
        self._validate(positions)
        self._out_of_beam_positions = positions

    def _validate(self, positions):
        # TODO raise something, catch in component
        if positions:
            filter_default = filter(lambda x: x.threshold is None, positions)
            if len(filter_default) == 0:
                raise Exception("ERROR: No default Out Of Beam Position defined for lookup.")
            if len(filter_default) > 1:
                raise Exception("ERROR: Multiple default Out Of Beam Position defined for lookup.")

    def get_position_for_intercept(self, beam_intercept):
        pos_above_threshold = filter(lambda x: x.threshold <= beam_intercept.y, self._out_of_beam_positions)
        return sorted(pos_above_threshold, reverse=True)[0]

    def is_in_beam(self, beam_intercept, displacement):
        if not self._out_of_beam_positions:
            return True

        out_of_beam_position = self.get_position_for_intercept(beam_intercept)
        return abs(displacement - out_of_beam_position.position) > out_of_beam_position.tolerance
