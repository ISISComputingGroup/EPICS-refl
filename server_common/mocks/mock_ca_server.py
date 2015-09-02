class MockCAServer(object):
    def __init__(self):
        self.pv_list = dict()

    def updatePV(self, pv_name, data):
        self.pv_list[pv_name] = data

    def deletePV(self, pv_name):
        del self.pv_list[pv_name]