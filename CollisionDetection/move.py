from transform import Transformation


class MoveError(Exception):
    def __init__(self, description):
        Exception.__init__(self)
        self.description = description

    def __str__(self):
        return self.description


def move_all(geometries, moves, monitors=None, values=None):
    if monitors is not None:
        axes = [m.value() for m in monitors]
    elif values is not None:
        axes = values
    else:
        raise MoveError("No monitors or values provided")

    if isinstance(moves, list):
        for move, geometry in zip(moves, geometries):
            apply_move(move(axes), geometry)
    else:
        for move, geometry in zip(moves(axes), geometries):
            apply_move(move, geometry)


def apply_move(move, geometry):
    if type(move) is Transformation:
        geometry.set_transform(move)
    elif move is None:
        pass
    else:
        t, s = move
        geometry.set_transform(t)
        if s is not None:
            geometry.set_size(**s)
