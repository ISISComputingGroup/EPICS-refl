import sys
import os
import ode
import logging
import threading
from time import sleep, time
from genie_python.genie_startup import *

import pv_server
import render
from configurations import config_zoom as config
from collide import collide, CollisionDetector
from geometry import GeometryBox
from move import move_all

sys.path.insert(0, os.path.abspath(os.environ["MYDIRCD"]))

from monitor import Monitor
from server_common.loggers.isis_logger import IsisLogger


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s (%(threadName)-2s) %(message)s',
                    )


def auto_seek(start_step_size, start_values, end_value, geometries, moves, axis_index, ignore, fine_step=None):
    limit = end_value
    current_value = start_values[axis_index]

    if current_value == end_value:
        return end_value

    values = start_values[:]

    last_value = None
    old_points = None

    step_checked = False

    if current_value < end_value:
        # Going up
        def comp(a, b):
            return a < b

        step_size = abs(start_step_size)
    else:
        # Going down
        def comp(a, b):
            return a > b

        step_size = -abs(start_step_size)

    while last_value is None or comp(last_value, end_value):
        # Move if we need to
        if last_value is not None:
            current_value += step_size
            # print "Using step size of %f" % step_size
        else:
            current_value = start_values[axis_index]

        if not comp(current_value, end_value):
            current_value = end_value

        values[axis_index] = current_value
        move_all(geometries, moves, values=values[:])

        # Check nothing moved too far
        if step_checked is False:
            new_points = [g.get_vertices() for g in geometries]
            if old_points is not None:
                delta = max_delta(geometries, new_points, old_points)
                if delta > start_step_size:
                    # Work out a new step size
                    step_size *= start_step_size/delta
                    last_value = None
                    continue
                step_checked = True

        # Check for collisions
        collisions = collide(geometries, ignore)

        if any(collisions):
            if current_value == start_values[axis_index]:
                # There was already a collision
                limit = current_value
                break
            elif fine_step and fine_step < step_size:
                start_values[axis_index] = last_value
                limit = auto_seek(fine_step, start_values, current_value, geometries, moves, axis_index, ignore)
            else:
                limit = last_value
            break

        old_points = new_points[:]
        last_value = current_value

    # print "Found limits for axis %d using step size of %f" % (axis_index, step_size)

    if limit is None:
        raise ValueError("Null limit")

    return limit


def max_delta(geometries, new_points, old_points):
    # Calculate the greatest position deltas
    delta = 0
    for j in range(len(geometries)):
        old = old_points[j]
        new = new_points[j]
        deltas = [map(float, n - o) for n, o in zip(new, old)]
        for i, (x, y, z) in enumerate(deltas):
            mag = float(x) ** 2 + float(y) ** 2 + float(z) ** 2
            if mag > delta:
                delta = mag
                # print "New max delta of %f (%f, %f, %f) for body %d at %s from %s" % \
                #       (mag ** 0.5, x, y, z, j, new[i], old[i])
    delta = float(delta) ** 0.5
    return delta


def compare(sign):
    if sign > 0:
        return lambda a, b: a > b
    else:
        return lambda a, b: a < b


def auto_seek_limits(geometries, ignore, moves, values, limits, coarse=1.0, fine=0.1):
    dynamic_limits = []
    for i in range(len(values)):
        logging.debug("Seeking for axis %d" % i)

        lower_limit = auto_seek(coarse, values[:], min(limits[i]), geometries, moves, i, ignore, fine)
        upper_limit = auto_seek(coarse, values[:], max(limits[i]), geometries, moves, i, ignore, fine)

        dynamic_limits.append([lower_limit, upper_limit])

        logging.debug("Found limits for axis %d at %s, %s" % (i, upper_limit, lower_limit))

    return dynamic_limits


def look_ahead(start_values, pvs, is_moving, geometries, moves, ignore, max_movement=1.0, max_time=10., time_step=0.1):
    # Get the indices of the axes currently moving
    moving = [i for i, m in enumerate(is_moving) if m == 0]  # DMOV = 0 when motors not moving

    msg = "No collisions predicted in the next %fs" % max_time
    safe_time = max_time
    safe = True

    # Only worth calculating if more than one axis is moving
    if len(moving) > 1:

        set_points = [None] * len(pvs)
        speeds = [None] * len(pvs)
        directions = [None] * len(pvs)

        # Assume everything has finished moving
        move_complete = [True] * len(pvs)

        # Get some settings:
        for i in moving:
            pv = pvs[i]

            set_point = get_pv(pv + '.DVAL')
            speed = get_pv(pv + '.VELO')

            direction = 0.
            move = set_point - start_values[i]
            if move > 0:
                direction = 1.
            if move < 0:
                direction = -1.

            set_points[i] = set_point
            speeds[i] = speed
            directions[i] = direction

            # This axis has not finished moving!
            move_complete[i] = False

        current_time = 0.
        values = start_values[:]
        old_points = None
        step_checked = False
        last_time = None

        while current_time < max_time:
            if last_time is None:
                values = start_values[:]
                current_time = 0.
                old_points = None
            else:
                current_time += time_step

            for i in moving:
                if move_complete[i] is False:
                    values[i] = start_values[i] + (directions[i] * speeds[i] * current_time)
                    comp = compare(directions[i])(values[i], set_points[i])
                    if comp:
                        values[i] = set_points[i]

            # Move the bodies
            move_all(geometries, moves, values=values)

            if step_checked is False:
                new_points = [g.get_vertices() for g in geometries]
                if old_points is not None:
                    delta = max_delta(geometries, new_points, old_points)

                    if delta > max_movement:
                        # Reduce the size of the time step
                        time_step *= max_movement/delta
                        # Reset to starting point
                        last_time = None
                        old_points = None
                        continue

                    step_checked = True

            # Check for collisions
            collisions = collide(geometries, ignore)

            if any(collisions):
                if last_time is None:
                    msg = "There is already a collision"
                    safe_time = 0.
                else:
                    msg = "Collision expected in %.1fs - %.1fs" % (last_time, current_time)
                    safe_time = last_time
                safe = False
                break

            old_points = new_points[:]
            last_time = current_time

    return msg, safe_time, safe


# Set the high and low dial limits for each motor
def set_limits(limits, pvs):
    for limit, pv in zip(limits, pvs):
        set_pv(pv + '.DLLM', limit[0])
        set_pv(pv + '.DHLM', limit[1])


# Contains operating mode events
class OperatingMode(object):
    def __init__(self):
        # Close event to be triggered by the render thread
        self.close = threading.Event()

        # Set dynamic limits automatically
        self.set_limits = threading.Event()

        # Stop the motors on a collision
        self.auto_stop = threading.Event()

        # Re-calculate limits on demand
        self.calc_limits = threading.Event()

    def get_operation_mode(self):
        return self.auto_stop.is_set(), self.set_limits.is_set(), self.close.is_set()

    def set_operation_mode(self, auto_stop, set_limits, close):
        if auto_stop:
            self.auto_stop.set()
        else:
            self.auto_stop.clear()

        if set_limits:
            self.set_limits.set()
        else:
            self.set_limits.clear()

        if close:
            self.close.set()
        else:
            self.close.clear()


# The main routine to execute
def main():
    # Load config:
    colors = config.colors
    moves = config.moves
    ignore = config.ignore
    pvs = config.pvs
    config_limits = config.hardlimits
    old_limits = config_limits[:]

    # Create space objects for the live and rendered world
    space = ode.Space()
    render_space = ode.Space()
    collision_space = ode.Space()

    # Create and populate lists of geometries
    geometries = []
    render_geometries = []
    collision_geometries = []
    for i, geometry in enumerate(config.geometries):
        geometries.append(GeometryBox(space, oversize=config.oversize, **geometry))
        render_geometries.append(GeometryBox(render_space, **geometry))
        collision_geometries.append(GeometryBox(collision_space, oversize=config.oversize, **geometry))

    # Create and populate two lists of monitors
    monitors = []
    is_moving = []
    for pv in pvs:
        m = Monitor(pv + ".DRBV")
        m.start()
        monitors.append(m)

        any_moving = Monitor(pv + ".DMOV")
        any_moving.start()
        is_moving.append(any_moving)

    # Create a shared operating mode object to control the main thread
    op_mode = OperatingMode()
    # Set the default behaviour to set_limits as calculated, and auto_stop on collision
    op_mode.set_limits.set()
    op_mode.auto_stop.set()

    # Start a logger
    logger = IsisLogger()

    # Create a shared render parameter object to update the render thread
    parameters = render.RenderParams()

    if 'blind' not in sys.argv:
        # Initialise the render thread, and set it to daemon - won't prevent the main thread from exiting
        renderer = render.Renderer(parameters, render_geometries, colors, monitors, pvs, moves, op_mode)
        renderer.daemon = True

    # Need to know if this is the first execution of the main loop
    op_mode.calc_limits.set()

    # Initialise the pv server
    # Loop over the pvdb and update the counts based on the number of aves/bodies
    for pv in pv_server.pvdb:
        for key, val in pv_server.pvdb[pv].items():
            if key == 'count':
                if val is pv_server.axis_count:
                    pv_server.pvdb[pv]['count'] = len(config.pvs)
                if val is pv_server.body_count:
                    pv_server.pvdb[pv]['count'] = len(config.geometries)

    driver = pv_server.start_thread(config.control_pv, op_mode)

    driver.setParam('OVERSIZE', config.oversize)
    driver.setParam('COARSE', config.coarse)
    driver.setParam('FINE', config.fine)
    driver.setParam('NAMES', [g['name'] for g in config.geometries])

    # Only report for new collisions
    collision_detector = CollisionDetector(driver, collision_geometries, config.moves, monitors, config.ignore,
                                           is_moving, logger, op_mode, config.pvs)
    collision_detector.start()

    # Main loop
    while True:

        # Freeze the positions of our current monitors by creating some dummies
        # This stops the threads from trying to reading each monitor sequentially, and holding each other up
        frozen = [m.value() for m in monitors]

        # Execute the move
        move_all(geometries, moves, values=frozen)

        # Check if the oversize has been changed, ahead of any collision calcs
        if driver.new_data.isSet():
            for geometry, collision_geometry in zip(geometries, collision_geometries):
                geometry.set_size(oversize=driver.getParam('OVERSIZE'))
                collision_geometry.set_size(oversize=driver.getParam('OVERSIZE'))
            driver.new_data.clear()
            op_mode.calc_limits.set()

        if driver.getParam("CALC") != 0:
            op_mode.calc_limits.set()

        collisions = collision_detector.collisions[:]
        collision_message = collision_detector.message[:]

        # Check if there have been any changes to the .MOVN monitors
        fresh = any([m.fresh() for m in is_moving])
        # Check if any of the motors monitors are moving
        moving = [not m.value() for m in is_moving]  # Invert because DMOV is inverted from MOVN
        any_moving = any(moving)

        new_limits = []

        if fresh or any_moving or op_mode.calc_limits.isSet():

            # Look ahead some time to see if any collisions are going to happen in the future
            msg, safe_time, safe = look_ahead(frozen, config.pvs, moving, geometries, moves, ignore,
                                              max_movement=driver.getParam('COARSE'))

            if not safe and not any(collisions):
                logger.write_to_log(msg, "MAJOR", "COLLIDE")
                driver.setParam('MSG', msg)
            else:
                driver.setParam('MSG', collision_message)

            logging.info(msg)

            # Start timing for diagnostics
            time_passed = time()

            # Seek the correct limit values
            dynamic_limits = auto_seek_limits(geometries, ignore, moves, frozen, config_limits,
                                              coarse=driver.getParam('COARSE'), fine=driver.getParam('FINE'))

            # Calculate and log the time taken to calculate
            time_passed = (time() - time_passed) * 1000

            # Log the new limits
            logging.info("New limits calculated in %dms, are %s" % (time_passed, dynamic_limits))

            # Set the limits according to the set_limits operating mode
            if op_mode.set_limits.is_set():
                # Apply the calculated limits
                new_limits = dynamic_limits[:]
            else:
                # Restore the configuration limits
                new_limits = config_limits[:]

            # Update the render thread parameters
            parameters.update_params(dynamic_limits, collisions, time_passed)

            # # Update the PVs
            driver.setParam('TIME', time_passed)
            driver.setParam('HI_LIM', [l[1] for l in dynamic_limits])
            driver.setParam('LO_LIM', [l[0] for l in dynamic_limits])
            driver.setParam('TRAVEL', [min([l[0] - m, l[1] - m], key=abs)
                                       for l, m in zip(dynamic_limits, frozen)])
            driver.setParam('TRAV_F', [l[1] - m for l, m in zip(dynamic_limits, frozen)])
            driver.setParam('TRAV_R', [l[0] - m for l, m in zip(dynamic_limits, frozen)])

            driver.updatePVs()

            if 'blind' not in sys.argv:
                # On the first run, start the renderer
                if renderer.is_alive() is False:
                    renderer.start()

            op_mode.calc_limits.clear()
            driver.setParam("CALC", False)
        else:
            # Restore the configuration limits
            if op_mode.set_limits.is_set() is False:
                new_limits = config_limits[:]

        # Stop us overloading the limits
        if not new_limits == old_limits:
            threading.Thread(target=set_limits, args=(new_limits, pvs)).start()

        old_limits = new_limits[:]

        # Exit the program
        if op_mode.close.is_set():
            # Restore the configuration limits
            set_limits(config_limits, pvs)
            return

        # Give the CPU a break
        sleep(0.01)

        if 'return' in sys.argv:
            return


# Execute main
main()
