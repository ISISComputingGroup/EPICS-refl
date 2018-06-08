from collections import Sequence
from transform import Transformation


def move_all(geometries, moves, monitors=None, values=None):
    """
    Applies moves to all axes in the given geometries.

    Args:
        geometries: A list of geometries. This list should have the same length as the list of moves provided.
        moves: A list of moves to apply
        Either:
            monitors: A list of monitor objects to get motor positions from
        Or:
            values: A list of the current motor positions
    """
    if monitors is not None:
        axes = [m.value() for m in monitors]
    elif values is not None:
        axes = values
    else:
        raise ValueError("No monitors or values provided")

    if isinstance(moves, list):
        for move, geometry in zip(moves, geometries):
            apply_move(move(axes), geometry)
    else:
        for move, geometry in zip(moves(axes), geometries):
            apply_move(move, geometry)


def apply_move(move, geometry):
    """
    Applies a move to an axis

    Args:
        move: Either:
            - None (do not move this axis)
            - A Transformation object to be applied
            - A tuple of two items (Transformation, Size), where the transformation will be applied and the size is a
                dictionary of sizes. Keys to the "size" dictionary are "x", "y", "z", and the values are numbers
                corresponding to the new size.
        geometry:
            The geometry to apply this move to.
    """
    if move is None:
        return
    elif isinstance(move, Transformation):
        geometry.set_transform(move)
    elif isinstance(move, Sequence) and len(move) == 2:
        t, s = move
        geometry.set_transform(t)
        if s is not None:
            geometry.set_size(**s)
    else:
        raise TypeError("Couldn't interpret move object of type {}: {}".format(move.__class__.__name__, move))
