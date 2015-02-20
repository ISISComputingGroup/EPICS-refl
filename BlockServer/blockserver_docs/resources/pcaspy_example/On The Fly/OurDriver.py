from pcaspy import SimpleServer, Driver
from OurServer import CAServer

pvdb = {
    'FIRST_NAME': {
        'type': 'char',
        'count': 1000,
    },
    'SURNAME': {
        'type': 'char',
        'count': 1000,
    },
    'FULLNAME': {
        'type': 'char',
        'count': 1000,
    },
}

prefix = "BLOCKSERVER:"

class NameServer(Driver):
    def __init__(self, server):
        super(NameServer, self).__init__()
        self.first_name = 'DOMINIC'
        self.surname = 'ORAM'

        self.server = server
        self.request_numbers = {}

    def read(self, reason):
        if reason == 'FULLNAME':
            value = self.first_name + "_" + self.surname
            self.updatePVs()
        else:
            value = self.getParam(reason)

        return value

    def write(self, reason, value):
        if reason == 'FIRST_NAME':
            self.first_name = value
            self.register_name()
        elif reason == 'SURNAME':
            self.surname = value
            self.register_name()

        self.setParam(reason, value)

    def register_name(self):
        full_name = self.first_name + "_" + self.surname

        # Update request numbers
        if self.request_numbers.get(full_name) is None:
            self.request_numbers[full_name] = 0
        else:
            self.request_numbers[full_name] += 1

        # Update PVs
        # self.server.registerPV(full_name)
        self.server.updatePV(full_name, str(self.request_numbers[full_name]))

if __name__ == '__main__':
    server = CAServer(prefix) #Create one of our servers

    server.createPV(prefix, pvdb)
    driver = NameServer(server)

    while True:
        server.process(0.1)