from pcaspy import SimpleServer, Driver
from pcaspy.tools import ServerThread
import random
import threading

# Use `caget -S` to print a char array as a string

# Configure this env with:
# `EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255`
# `EPICS_CAS_INTF_ADDR_LIST=127.0.0.1`

# Unique objects for updating counts with the number of axes/bodies
axis_count = object()
body_count = object()

pvdb = {
    'RAND': {
        'prec': 3,
        # 'scan' : 1,
        'count': 1,
        'type': 'float',
    },
    'MSG': {
        'count': 300,
        'type': 'char',
    },
    'NAMES': {
        'count': body_count,
        'type': 'string',
    },
    'MODE': {
        'count': 1,
        'type': 'int',
        'scan': 1,
    },
    'AUTO_STOP': {
        'count': 1,
        'type': 'int',
    },
    'AUTO_LIMIT': {
        'count': 1,
        'type': 'int',
    },
    'SAFE': {
        'count': 1,
        'type': 'int',
    },
    'HI_LIM': {
        'count': axis_count,
        'type': 'float',
        'prec': 3,
    },
    'LO_LIM': {
        'count': axis_count,
        'type': 'float',
        'prec': 3,
    },
    'TRAVEL': {
        'count': axis_count,
        'type': 'float',
        'prec': 3,
    },
    'TRAV_F': {
        'count': axis_count,
        'type': 'float',
        'prec': 3,
    },
    'TRAV_R': {
        'count': axis_count,
        'type': 'float',
        'prec': 3,
    },
    'COLLIDED': {
        'count': body_count,
        'type': 'int',
    },
    'OVERSIZE': {
        'count': 1,
        'type': 'float',
        'prec': 3,
        'unit': 'mm',
    },
    'COARSE': {
        'count': 1,
        'type': 'float',
        'prec': 3,
    },
    'FINE': {
        'count': 1,
        'type': 'float',
        'prec': 3,
    },
    'TIME': {
        'count': 1,
        'type': 'int',
        # 'scan': 1,
    },
    'CALC': {
        'count': 1,
        'type': 'int',
    },
}


class MyDriver(Driver):
    def __init__(self, op_mode):
        super(MyDriver, self).__init__()
        self.op_mode = op_mode

        self.new_data = threading.Event()

    def read(self, reason):
        # logging.debug("Reading '%s'...", reason)
        if reason == 'RAND':
            value = random.random()
        elif reason == 'MODE':
            self.setParam(reason, self.op_mode.code)
            value = self.getParam(reason)
        elif reason == 'AUTO_STOP':
            value = int(self.op_mode.auto_stop.is_set())
        elif reason == 'AUTO_LIMIT':
            value = int(self.op_mode.set_limits.is_set())
        else:
            value = self.getParam(reason)

        return value

    def write(self, reason, value):
        status = True
        if reason == 'MODE':
            self.op_mode.code = int(value)
            self.setParam(reason, int(value))
        elif reason == 'AUTO_STOP':
            if value == 1:
                self.op_mode.auto_stop.set()
            elif value == 0:
                self.op_mode.auto_stop.clear()
            self.setParam('MODE', self.op_mode.code)
        elif reason == 'AUTO_LIMIT':
            if value == 1:
                self.op_mode.set_limits.set()
            elif value == 0:
                self.op_mode.set_limits.clear()
        elif reason == 'OVERSIZE':
            self.setParam(reason, value)
            self.setParam('COARSE', 4 * value)
        elif reason == 'COARSE':
            self.setParam(reason, value)
            self.setParam('OVERSIZE', value / 4)
        elif reason == 'FINE':
            self.setParam(reason, value)
        elif reason == 'CALC':
            self.setParam(reason, True)

        self.new_data.set()
        return status


def start_thread(prefix, op_mode):

    server = SimpleServer()
    server.createPV(prefix, pvdb)
    # server.setDebugLevel(4)

    server_thread = ServerThread(server)
    server_thread.name = "PVServer"
    server_thread.daemon = True
    server_thread.start()

    driver = MyDriver(op_mode)

    return driver
