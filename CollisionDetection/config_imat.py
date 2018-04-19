from math import radians
from transform import Transformation
import os
import numpy as np

# Config happens here:

# Colors for each body
GREY = (0.6, 0.6, 0.6)
MAGENTA = (1, 0, 1)
YELLOW = (1, 1, 0)
CYAN = (0, 1, 1)
GREEN = (0, 1, 0)
ORANGE = (1, 0.5, 0)
LIGHT_BLUE = (0.2, 0.2, 1)
WHITE = (1, 1, 1)

# Colors for each body
colors = [GREY, MAGENTA, YELLOW, CYAN, GREEN, ORANGE, LIGHT_BLUE, WHITE]

# PV prefix
pv_prefix = os.environ["MYPVPREFIX"]

# PV prefix for controlling the system
control_pv = "{}COLLIDE:".format(pv_prefix)

# Define the geometry of the system in mm
# Coordinate origin at arc centre, with nominal beam height
# Size is defined x, y, z (x is beam, z is up) TODO: use point
base = dict(name="Z_Stage", size=(1500.0, 1500.0, 2650.0), color=GREY)  # Initial height is halfway across travel
carriage = dict(name="Carriage", size=(700.0, 700.0, 40.0), color=YELLOW)
tom_base = dict(name="Tomography_Base", size=(250.0, 250.0, 233.0), color=CYAN)
tom_top = dict(name="Tomography_Top", size=(360.0, 360.0, 18.0), color=YELLOW)

incident_slits = dict(name="Incident_Slits", position=(-1200, 0, 0), size=(80.0, 300.0, 300.0), color=WHITE) # fixed for now

# Stationary objects
camera = dict(name="Camera", position=(800.0+440.0/2, 0, -392), size=(440.0, 440.0, 1245.0), color=WHITE)

sample = dict(name="Sample", size=(250.0, 250.0, 150.0), color=WHITE)

# Arc centre as distance between the centre of objects and the point about which they rotate
tom_arc = 76.0

# Define some search parameters
coarse = 20.0
fine = 0.5

# Define the oversized-ness of each body - a global value in mm
oversize = coarse / 4

# Put them in a list
geometries = [base, carriage, tom_base, tom_top, sample, incident_slits, camera]

# List of pairs to ignore [0, 1]...[7, 8]
ignore = []
for i in range(0, 5):
    for j in range(i, 5):
        ignore.append([i, j])


def moves(axes):
    # Z stage
    t = Transformation()

    initial_base_height = base['size'][2]

    new_height = axes[6] + initial_base_height

    dist_beam_to_base = 3780

    t.translate(z=-dist_beam_to_base + new_height / 2)

    yield t, dict(z=new_height)

    # Carriage movement
    t = Transformation()

    # Set new height due to base
    carriage_height = carriage['size'][2]
    t.translate(z=-dist_beam_to_base + new_height + carriage_height/2)

    # Rotation of base
    t.rotate(rz=radians(axes[5]))

    # X stage
    t.translate(x=axes[3], forward=False)

    # Y stage
    t.translate(y=axes[4], forward=False)

    yield t

    # Tomography base is attached to carriage
    t = Transformation(t)

    t.translate(z=tom_base['size'][2]/2)

    yield t

    # Tomograghy top
    u = Transformation()

    u.rotate(rz=radians(axes[0]))

    u.translate(z=-tom_arc)
    u.rotate(rx=radians(axes[1]))
    u.rotate(ry=radians(axes[2]))
    u.translate(z=tom_arc)

    v = Transformation()
    v.matrix = np.dot(u.matrix, t.matrix) # This may be wrong order or may not be needed if you use t as a starting point for u

    yield v

    # Sample is fixed to the top of the tomography
    t = Transformation(v)

    t.translate(z=sample['size'][2]/2, forward=False)
    yield t



#TODO: Refactor pvs and limits into nicer structure

# Attach monitors to readbacks
pvs = ["{}MOT:MTR0502", "{}MOT:MTR0503", "{}MOT:MTR0504",  # Tomography Phi, Chi, Theta
       "{}MOT:MTR0505", "{}MOT:MTR0506",  # Sample Stack X, Y
       "{}MOT:MTR0901", "{}MOT:MTR0902"  # Beckhoff rot & z
       ]

pvs = [pv.format(pv_prefix) for pv in pvs]

hardlimits = [[-90, 270], [-6, 6], [-6, 6],
              [105, 1005], [105, 1005],
              [180, -180], [-250, 250]]
