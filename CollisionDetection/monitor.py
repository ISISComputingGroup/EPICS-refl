from CaChannel import CaChannel
from CaChannel import CaChannelException
import ca
import threading
import time


class Monitor(object):

    def __init__(self, pv):
        self.pv = pv
        self.val = None
        self.channel = CaChannel()
        self.running = False
        self.lock = threading.Lock()
        self.stale = True

    def start(self):
        if self.running:
            self.stop()

        try:
            self.channel.searchw(self.pv)
        except CaChannelException:
            print ("Unable to find pv " + self.pv)
            return

        # Create the CA monitor callback
        self.channel.add_masked_array_event(
            ca.dbf_type_to_DBR_STS(self.channel.field_type()),
            None,
            ca.DBE_VALUE,
            self.update,
            None)
        self.channel.pend_event()
        self.running = True

    def update(self, epics_args, user_args):
        with self.lock:
            self.val = epics_args['pv_value']
            self.stale = False

    def value(self):
        with self.lock:
            self.stale = True
            return self.val

    def fresh(self):
        with self.lock:
            fresh = not self.stale
            self.stale = True
            return fresh

    def stop(self):
        self.channel.clear_event()
        self.running = False


class MonitorQueue(Monitor):
    def __init__(self, pv, initial=None):
        self.queue = []
        self.time = None
        self.frozen = False
        if initial:
            self.queue.append(initial)
        Monitor.__init__(self, pv)

    def update(self, epics_args, user_args):
        value = epics_args['pv_value']
        if value == self.last():
            # Duplicate value
            pass
        else:
            if not self.frozen:
                with self.lock:
                    self.queue.append(value)
                    self.time = time.time()

    def clear(self):
        """
        Sets the queue to the last value
        """
        with self.lock:
            self.queue[:] = [self.queue[-1]]

    def reset(self):
        """
        Sets the queue to the first value
        """
        with self.lock:
            self.queue[:] = [self.queue[0]]

    def initialised(self):
        """
        Is the queue populated?
        """
        with self.lock:
            if len(self.queue) > 0:
                return True
            else:
                return False

    def first(self):
        with self.lock:
            if len(self.queue) > 0:
                return self.queue[0]
            else:
                return None

    def last(self):
        with self.lock:
            if len(self.queue) > 0:
                return self.queue[-1]
            else:
                return None

    def changed(self):
        with self.lock:
            if self.first() == self.last():
                return False
            else:
                return True


class DummyMonitor(object):
    def __init__(self, value):
        self.val = None
        self.update(value)

    def update(self, value):
        self.val = value

    def value(self):
        return self.val
