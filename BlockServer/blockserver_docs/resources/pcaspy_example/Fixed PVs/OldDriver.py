from pcaspy import SimpleServer, Driver

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
    def __init__(self):
        super(NameServer, self).__init__()
        self.first_name = 'DOMINIC'
        self.surname = 'ORAM'

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
        elif reason == 'SURNAME':
            self.surname = value

        self.setParam(reason, value)

if __name__ == '__main__':
    server = SimpleServer() #Create a simple server

    server.createPV(prefix, pvdb)
    driver = NameServer()

    while True:
        server.process(0.1)