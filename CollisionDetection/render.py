import pygame
import os
from OpenGL.GL import *
from OpenGL.GL.VERSION.GL_1_0 import glLoadMatrixd
from OpenGL.GL.exceptional import glBegin, glEnd
from OpenGL.GL.images import glDrawPixels
from OpenGL.raw.GL.VERSION.GL_1_0 import glViewport, glMatrixMode, glLoadIdentity, glEnable, glShadeModel, \
    glClearColor, glClear, glPushMatrix, glOrtho, glDisable, glPopMatrix, glRasterPos2d
from OpenGL.raw.GL.VERSION.GL_1_1 import GL_PROJECTION, GL_MODELVIEW, GL_DEPTH_TEST, GL_FLAT, GL_COLOR_MATERIAL, \
    GL_LIGHTING, GL_LIGHT0, GL_POSITION, GL_FRONT, GL_AMBIENT, GL_DIFFUSE, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, \
    GL_CULL_FACE, GL_RGBA, GL_LINES
from OpenGL.raw.GL.VERSION.GL_4_0 import GL_QUADS
from OpenGL.raw.GL._types import GL_UNSIGNED_BYTE
from OpenGL.raw.GLU import gluPerspective
from pygame.constants import HWSURFACE, OPENGL, DOUBLEBUF, QUIT, KEYUP, K_ESCAPE, K_LEFT, K_RIGHT, K_DOWN, K_UP, K_z, \
    K_x, K_w, K_s, K_a, K_d, K_q, K_e, K_1, K_2, K_3, K_4, K_SPACE, K_RETURN

import threading
import logging

import numpy as np
from transform import Transformation

from move import move_all


# Camera transform matrix
def initialise_camera(transform):
    transform.identity()

    transform.translate(0, 400, 1600)
    transform.rotate(-0.8, 0.5, 0)
    transform.rotate(0, 0, -2.5, forward=False)
    transform.translate(-200, 200, 200)
    return transform

screensize = (820, 720)

os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (5, 25)

clock = pygame.time.Clock()

# Need a toggle to allow moving away from a crash
stopMotors = False
autoRestart = False

heartbeat = 0
time_passed = 0

font = None

camera_transform = Transformation()
initialise_camera(camera_transform)

# Initialize speeds and directions for camera
rotation_speed = 0.7
movement_speed = 250.0


def glinit():
    pygame.init()

    pygame.display.set_mode(screensize, HWSURFACE | OPENGL | DOUBLEBUF)

    global font
    font = pygame.font.SysFont("consolas", 18)

    pygame.display.set_caption("Collision Monitor")

    # set the screen size
    glViewport(0, 0, screensize[0], screensize[1])
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # FOV angle, aspect ratio, near clipping plane, far clipping plane
    gluPerspective(60.0, float(screensize[0]) / screensize[1], 500, 10000.)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # setup GL stuff

    glEnable(GL_DEPTH_TEST)

    glShadeModel(GL_FLAT)
    glClearColor(0, 0, 0, 0.0)

    glEnable(GL_COLOR_MATERIAL)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    glLight(GL_LIGHT0, GL_POSITION, [0, 0, 0])

    glLight(GL_LIGHT0, GL_AMBIENT, (.1, .1, .1, 1.))
    glLight(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.))

    glMaterial(GL_FRONT, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
    glMaterial(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

    # Clear the screen, and z-buffer
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


class Renderer(threading.Thread):
    def __init__(self, parameters, geometries, colors, monitors, pvs, moves, op_mode):
        threading.Thread.__init__(self, name="Renderer")

        self.geometries = geometries

        self.colors = colors
        self.monitors = monitors
        self.pvs = pvs
        self.moves = moves

        self.parameters = parameters
        self.op_mode = op_mode

    def run(self):
        self.op_mode.close.clear()
        glinit()
        while self.op_mode.close.is_set() is False:
            frozen = [monitor.value() for monitor in self.monitors]
            loop(self, frozen)


def check_controls(renderer):
    global camera_transform, stopMotors, autoRestart, time_passed

    for event in pygame.event.get():
        if event.type == QUIT:
            renderer.op_mode.close.set()
            return
        if event.type == KEYUP and event.key == K_ESCAPE:
            renderer.op_mode.close.set()
            return

    time_passed = clock.tick()
    time_passed_seconds = time_passed / 1000.

    logging.debug("Frame drawn in %d", time_passed)

    pressed = pygame.key.get_pressed()

    # Reset rotation and movement directions
    rotation_direction = np.array((0.0, 0.0, 0.0))
    movement_direction = np.array((0.0, 0.0, 0.0))

    # Modify direction vectors for key presses
    if pressed[K_LEFT]:
        rotation_direction[1] = -1.0
    elif pressed[K_RIGHT]:
        rotation_direction[1] = +1.0
    if pressed[K_DOWN]:
        rotation_direction[0] = -1.0
    elif pressed[K_UP]:
        rotation_direction[0] = +1.0
    if pressed[K_z]:
        rotation_direction[2] = +1.0
    elif pressed[K_x]:
        rotation_direction[2] = -1.0
    if pressed[K_w]:
        movement_direction[2] = -1.0
    elif pressed[K_s]:
        movement_direction[2] = +1.0
    if pressed[K_a]:
        movement_direction[0] = -1.0
    elif pressed[K_d]:
        movement_direction[0] = +1.0
    if pressed[K_q]:
        movement_direction[1] = -1.0
    elif pressed[K_e]:
        movement_direction[1] = +1.0
    if pressed[K_1]:
        renderer.op_mode.auto_stop.set()
    elif pressed[K_2]:
        renderer.op_mode.auto_stop.clear()
    if pressed[K_3]:
        renderer.op_mode.set_limits.set()
    elif pressed[K_4]:
        renderer.op_mode.set_limits.clear()
    if pressed[K_SPACE]:
        initialise_camera(camera_transform)
    if pressed[K_RETURN]:
        renderer.op_mode.calc_limits.set()

    # Calculate camera rotation
    rotation = np.array(rotation_direction * rotation_speed * time_passed_seconds)
    camera_transform.rotate(*rotation, forward=False)

    # Calculate camera movement
    movement = np.array(movement_direction * movement_speed * time_passed_seconds)
    camera_transform.translate(*movement, forward=False)

    # Light must be transformed as well
    glLight(GL_LIGHT0, GL_POSITION, (0.0, 0.0, -1.0, 1.0))

    # Upload the inverse camera matrix to OpenGL
    glLoadMatrixd(np.reshape(camera_transform.get_inverse().transpose(), 16))


def square(x, y, w=50, h=50, color=(1, 0, 0)):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, screensize[0], screensize[1], 0, 0, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glDisable(GL_CULL_FACE)
    glClear(GL_DEPTH_BUFFER_BIT)
    glColor(color)
    glBegin(GL_QUADS)
    glVertex((x, y))
    glVertex((x + w, y))
    glVertex((x + w, y + h))
    glVertex((x, y + h))
    glEnd()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def text(x, y, string, color=(0.4, 0.4, 0.4), align="left"):
    color = [c * 255 for c in color]
    color.append(255)

    y += 18

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, screensize[0], screensize[1], 0, 0, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glDisable(GL_CULL_FACE)
    glClear(GL_DEPTH_BUFFER_BIT)
    glColor(color)

    text_surface = font.render(string, True, color, (0, 0, 0, 255))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    if align is "right":
        glRasterPos2d(x - text_surface.get_width(), y)
    else:
        glRasterPos2d(x, y)

    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    return text_surface.get_width() + x


# Render the geometry - can supply color to override the geometry's own color e.g. make it red when collided
def render_box(geometry, color=None, fill=True):
    num_faces = 6
    num_edges = 12

    normals = [(0.0, 0.0, +1.0),  # top
               (0.0, 0.0, -1.0),  # bot
               (-1.0, 0.0, 0.0),  # left
               (+1.0, 0.0, 0.0),  # right
               (0.0, +1.0, 0.0),  # front
               (0.0, -1.0, 0.0),  # back
               ]

    vertex_indices = [(0, 1, 2, 3),  # front
                      (4, 5, 6, 7),  # back
                      (1, 5, 6, 2),  # right
                      (0, 4, 7, 3),  # left
                      (3, 2, 6, 7),  # top
                      (0, 1, 5, 4)]  # bottom

    edge_indices = [(0, 1),
                    (1, 2),
                    (2, 3),
                    (3, 0),
                    (4, 5),
                    (5, 6),
                    (6, 7),
                    (7, 4),
                    (0, 4),
                    (1, 5),
                    (2, 6),
                    (3, 7)]

    # Set the color for rendering
    if color:
        glColor(color)
    else:
        glColor(geometry.color)

    # Get all the vertices of the body
    vertices = geometry.get_vertices()

    # Get the rotation of the geometry
    rot = geometry.geom.getRotation()
    rot = np.reshape(rot, (3, 3))

    # If we want a filled in cube:
    if fill:
        # Start drawing quads
        glBegin(GL_QUADS)

        # Draw all 6 faces of the cube
        for face_no in xrange(num_faces):
            # Calculate and apply the normal - for lighting
            normal = np.array(normals[face_no]).T
            rotated = np.dot(normal, rot)
            glNormal3dv(rotated)

            # Calculate and draw each vertex
            for i in vertex_indices[face_no]:
                glVertex(vertices[i])

        # Stop drawing quads
        glEnd()

    # We want a wire frame:
    else:
        glNormal3dv([0, 0, 1])
        # Start drawing lines
        glBegin(GL_LINES)

        # Draw all 12 edges of the cube
        for edge_no in xrange(num_edges):
            # Get the vertices for each edge
            vertex_index = edge_indices[edge_no]

            # Calculate and draw each vertex
            for i in vertex_index:
                glVertex(vertices[i])

        # Stop drawing lines
        glEnd()


def draw(renderer, frozen):
    softlimits, collisions, duration = renderer.parameters.get_params()

    global stopMotors, autoRestart, heartbeat, time_passed, camera_transform

    # Clear the screen, and z-buffer
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # A patch at the origin
    # glColor((1, 0, 0))
    # glBegin(GL_QUADS)
    # glVertex((10, 10, 0))
    # glVertex((10, -10, 0))
    # glVertex((-10, -10, 0))
    # glVertex((-10, 10, 0))
    # glEnd()

    move_all(renderer.geometries, renderer.moves, values=frozen)
    # Render!
    for geometry, collided in zip(renderer.geometries, collisions):
        if collided:
            # geometry.render((0.8, 0, 0))
            render_box(geometry, (0.8, 0, 0))
        else:
            # geometry.render()
            render_box(geometry)

    # Set the HUD normal to the camera's position - gives us full illumination?
    glNormal3dv([0., -1., 0.])

    # Display the status icon
    if any(collisions):
        if renderer.op_mode.auto_stop.is_set():
            # Red
            square(10, 10)
            text(70, 10, "Collision detected!")
        else:
            # Orange
            square(10, 10, color=(1, 0.5, 0))
            text(70, 10, "Collision ignored!")
    else:
        if renderer.op_mode.auto_stop.is_set():
            if renderer.op_mode.set_limits.is_set():
                # Green
                square(10, 10, color=(0, 1, 0))
            else:
                # Cyan
                square(10, 10, color=(0, 1, 1))
            text(70, 10, "Stop on collision")
        else:
            if renderer.op_mode.set_limits.is_set():
                # Yellow
                square(10, 10, color=(1, 1, 0))
            else:
                # Blue
                square(10, 10, color=(0, 0, 1))
            text(70, 10, "Ignoring collisions")

    if renderer.op_mode.set_limits.is_set():
        text(70, 35, "Setting limits")
    else:
        text(70, 35, "Not setting limits")

    for i, (monitor, limit) in enumerate(zip(frozen, softlimits)):
        text(80 * 1, 70 + (30 * i), "%.2f" % limit[0], renderer.colors[i % len(renderer.colors)], align="right")
        text(80 * 2, 70 + (30 * i), "%.2f" % monitor, renderer.colors[i % len(renderer.colors)], align="right")
        text(80 * 3, 70 + (30 * i), "%.2f" % limit[1], renderer.colors[i % len(renderer.colors)], align="right")

    if duration > 0:
        text(screensize[0] - 10, screensize[1] - 45, "%.0f" % duration, align="right")

    text(screensize[0] - 10, screensize[1] - 25, "%.0f" % time_passed, align="right")

    # Show a heartbeat bar
    heartticks = 100
    square(0, screensize[1] - 5, screensize[0] * heartbeat / heartticks, 5, (0.3, 0.3, 0.3))
    if heartbeat > heartticks:
        heartbeat = 0
        # Need to return for sensible profiling
        # return
    else:
        heartbeat += 1

    # Show the screen
    pygame.display.flip()

    pygame.time.wait(max(50 - time_passed, 0))


def loop(renderer, monitors):
    check_controls(renderer)
    if renderer.op_mode.close.is_set() is False:
        if renderer.parameters.stale is False:
            # wait for fresh values??
            draw(renderer, monitors)


class RenderParams(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.softlimits = []
        self.collisions = []
        self.duration = None
        self.stale = True

    def update_params(self, softlimits, collisions, duration):
        with self.lock:
            logging.debug("Acquired lock for update")
            self.softlimits = softlimits
            self.collisions = collisions
            self.duration = duration

            if self.stale:
                self.stale = False
                pass

    def get_params(self):
        with self.lock:
            logging.debug("Acquired lock for read")
            # self.stale = True
            return self.softlimits, self.collisions, self.duration
