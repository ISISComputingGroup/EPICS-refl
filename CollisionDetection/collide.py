import logging
import threading
from time import sleep

import numpy as np
import ode
from genie_python.genie import set_pv

from move import move_all


def collide(geometries, ignore):
    """
    Calculates which of the given geometries will collide, ignoring geometries that are specified as ignored.
    As there are only [(len(geometries)-1)!] combinations, and we don't care about some, there isn't much effort saved
    by using spaces (which do a quicker estimate of collisions first)
    :param geometries: A list of GeometryBox objects to check for collisions.
    :param ignore: A list of pairs to ignore. Each pair is represented by a list with two entries.
    :return: A list of booleans, each corresponding to a geometry by position, True if the geometry has collided.
    """
    collisions = [False] * len(geometries)
    for i, geom1 in enumerate(geometries):
        for j, geom2 in enumerate(geometries[i:]):
            if not ([i, i + j] in ignore or [i + j, i] in ignore):
                contacts = ode.collide(geom1.geom, geom2.geom)
                if contacts:
                    collisions[i] = True
                    collisions[i + j] = True
    return collisions


def detect_collisions(collision_reported, driver, geometries, ignore, is_moving, logger, op_mode, pvs):
    # Check for collisions
    collisions = collide(geometries, ignore)
    # Get some data to the user:
    driver.setParam('COLLIDED', [int(c) for c in collisions])
    # If there has been a collision:
    if any(collisions):
        # Message:
        msg = "Collisions on %s" % ", ".join(map(str, [geometries[i].name for i in np.where(collisions)[0]]))

        # Log the collisions
        logging.debug("Collisions on %s", [i for i in np.where(collisions)[0]])
        # driver.setParam('MSG', msg)
        driver.setParam('SAFE', 0)

        # Log to the IOC log
        if not collisions == collision_reported:
            logger.write_to_log(msg, "MAJOR", "COLLIDE")
            collision_reported = collisions[:]

        # Stop the moving motors based on the operating mode auto_stop
        if op_mode.auto_stop.is_set():
            logging.debug("Stopping motors %s" % [i for i, m in enumerate(is_moving) if m.value()])
            for moving, pv in zip(is_moving, pvs):
                if moving.value():
                    set_pv(pv + '.STOP', 1)
    else:
        # driver.setParam('MSG', "No collisions detected.")
        msg = "No collisions detected."
        driver.setParam('SAFE', 1)
        collision_reported = None

    return collisions, collision_reported, msg


class CollisionDetector(threading.Thread):
    def __init__(self, driver, geometries, moves, monitors, ignore, is_moving, logger, op_mode, pvs):
        threading.Thread.__init__(self, name="CollisionDetector")

        self.driver = driver
        self.geometries = geometries
        self.moves = moves
        self.monitors = monitors
        self.ignore = ignore
        self.is_moving = is_moving
        self.logger = logger
        self.op_mode = op_mode
        self.pvs = pvs

        self._lock_message = threading.Lock()
        self._message = "Nothing to report!"
        self._lock_collisions = threading.Lock()
        self._collisions = [0] * len(geometries)

        self.setDaemon(True)

    def run(self):
        collision_reported = None
        while True:
            move_all(self.geometries, self.moves, monitors=self.monitors)
            collisions, collision_reported, message = \
                detect_collisions(collision_reported, self.driver, self.geometries, self.ignore, self.is_moving,
                                  self.logger, self.op_mode, self.pvs)
            self.collisions = collisions
            self.message = message
            sleep(0.05)

    @property
    def collisions(self):
        with self._lock_collisions:
            return self._collisions[:]

    @collisions.setter
    def collisions(self, collisions):
        with self._lock_collisions:
            self._collisions = collisions\

    @property
    def message(self):
        with self._lock_message:
            return self._message[:]

    @message.setter
    def message(self, msg):
        with self._lock_message:
            self._message = msg

