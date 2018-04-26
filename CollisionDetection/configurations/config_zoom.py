from transform import Transformation
import os

# Config happens here:

# Colors for each body
MAGENTA = (1, 0, 1)
YELLOW = (1, 1, 0)

# Colors for each body
colors = [MAGENTA, YELLOW]

# PV prefix
pv_prefix = os.environ["MYPVPREFIX"]

# PV prefix for controlling the system
control_pv = "{}COLLIDE:".format(pv_prefix)

# Define the geometry of the system in mm
# Coordinate origin at arc centre, with nominal beam height
# Size is defined x, y, z (x is beam, z is up)

detector_x_size = 1000
baffle_x_size = 1000

detector = dict(name="Detector", size=(detector_x_size, 1000.0, 1000.0), color=MAGENTA)
baffle = dict(name="Baffle", size=(baffle_x_size, 1000.0, 1000.0), color=YELLOW)

# Define some search parameters
coarse = 20.0
fine = 0.5

# Define the oversized-ness of each body - a global value in mm
oversize = coarse / 4

# Put them in a list
geometries = [detector, baffle]

ignore = []


def moves(axes):

    baffle_to_detector_zero = 5789.74

    # Detector
    t = Transformation()
    t.translate(x=baffle_to_detector_zero - detector_x_size + axes[0])

    yield t

    # Baffle
    t = Transformation()
    t.translate(x=-axes[1] + baffle_x_size)

    yield t

# Attach monitors to readbacks
pvs = [
    "{}MOT:MTR0101",
    "{}MOT:MTR0102",
]

pvs = [pv.format(pv_prefix) for pv in pvs]

hardlimits = [
    [-10000, 10000],
    [-10000, 10000],
]
