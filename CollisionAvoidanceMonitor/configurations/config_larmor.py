from math import radians
from transform import Transformation
import os

# Config happens here:

# Colors for each body
colors = [(0.6, 0.6, 0.6), (1, 0, 1), (1, 1, 0), (0, 1, 1), (0, 1, 0), (1, 0.5, 0), (0.2, 0.2, 1), (1, 1, 1)]

# PV prefix
pv_prefix = os.environ["MYPVPREFIX"]

# PV prefix for controlling the system
control_pv = "{}COLLIDE:".format(pv_prefix)

# Define the geometry of the system in mm
# Coordinate origin at arc centre, with nominal beam height
z_stage = dict(name="Z_Stage", size=(1000.0, 1000.0, 630.0), color=colors[0])
rot_stage = dict(name="Rotation", size=(600.0, 600.0, 165.0), color=colors[1])
bot_arc = dict(name="Bottom_Arc", size=(600.0, 600.0, 120.0), color=colors[2])
top_arc = dict(name="Top_Arc", size=(600.0, 600.0, 120.0), color=colors[3])
fine_z = dict(name="Fine_Z", size=(600.0, 600.0, 120.0), color=colors[4])
y_base = dict(name="Y_Stage", size=(900.0, 1200.0, 50.0), color=colors[4])
y_stage = dict(name="Y_Carriage", size=(600.0, 300.0, 20.0), color=colors[5])
x_stage = dict(name="X_Carriage", size=(520.0, 300.0, 20.0), color=colors[6])
sample = dict(name="Sample", size=(250.0, 250.0, 150.0), color=colors[6])
snout = dict(name="Snout", position=(-300, 0, 0), size=(500, 70, 70), color=colors[7])
slits = dict(name="Slits", position=(450, 0, 0), size=(100, 300, 300), color=colors[7])

# Define some variables to describe the geometry
centre_arc = 750.0
beam_ref = 1625.0

# Define some search parameters
coarse = 20.0
fine = 0.5

# Define the oversized-ness of each body - a global value in mm
oversize = coarse / 4

# List of pairs to ignore [0, 1]...[7, 8]
ignore = []
for i in range(0, 9):
    for j in range(i, 9):
        ignore.append([i, j])


def move_everything(axes):
    # Z stage
    t = Transformation()

    size = axes[0] + z_stage['size'][2]

    t.translate(z=-beam_ref + size / 2)

    yield t, dict(z=size)

    # Rotation
    t = Transformation()
    t.translate(z=-beam_ref + axes[0] + z_stage['size'][2] + rot_stage['size'][2] / 2)
    t.rotate(rz=radians(axes[1]))

    yield t

    # Bottom arc
    t = Transformation()

    t.translate(z=-centre_arc - (bot_arc['size'][2] / 2 + top_arc['size'][2]))
    t.rotate(ry=radians(axes[2]))
    t.translate(z=centre_arc + (bot_arc['size'][2] / 2 + top_arc['size'][2]))

    t.translate(z=-beam_ref + axes[0] + z_stage['size'][2] + rot_stage['size'][2] + bot_arc['size'][2] / 2)
    t.rotate(rz=radians(axes[1]))

    yield t

    # Top arc
    t = Transformation(t)

    t.translate(z=+(centre_arc + top_arc['size'][2] / 2), forward=False)
    t.rotate(rx=radians(axes[3]), forward=False)
    t.translate(z=-(centre_arc + top_arc['size'][2] / 2), forward=False)

    t.translate(z=top_arc['size'][2] / 2 + bot_arc['size'][2] / 2, forward=False)
    yield t

    # Fine Z
    u = Transformation(t)

    size = axes[4] + fine_z['size'][2]

    u.translate(z=size / 2 + top_arc['size'][2] / 2, forward=False)

    yield u, dict(z=size)

    # Base of Y stage (top of fine Z)
    t = Transformation(t)

    size = axes[4] + fine_z['size'][2]

    t.translate(z=size + top_arc['size'][2] / 2 + y_base['size'][2] / 2, forward=False)

    yield t

    # Y stage
    t = Transformation(t)

    t.translate(y=axes[5], z=y_base['size'][2] / 2 + y_stage['size'][2] / 2, forward=False)

    yield t

    # X stage
    t = Transformation(t)

    t.translate(x=axes[6], z=y_stage['size'][2] / 2 + x_stage['size'][2] / 2, forward=False)

    yield t

    # Sample
    t = Transformation(t)

    t.translate(z=x_stage['size'][2] / 2 + sample['size'][2] / 2, forward=False)

    yield t


moves = move_everything

# Put them in a list
geometries = [z_stage, rot_stage, bot_arc, top_arc, fine_z, y_base, y_stage, x_stage, sample, snout, slits]

# Attach monitors to readbacks
pvs = ["{}MOT:MTR0101",
       "{}MOT:MTR0102",
       "{}MOT:MTR0103",
       "{}MOT:MTR0104",
       "{}MOT:MTR0105",
       "{}MOT:MTR0106",
       "{}MOT:MTR0107"]

pvs = [pv.format(pv_prefix) for pv in pvs]

hardlimits = [[-220, 100],
              [-180.0, 180.0],
              [-20, 20.0],
              [-20.0, 20.0],
              [0.0, 30.0],
              [-300, 300],
              [-37.5, 37.5]]
