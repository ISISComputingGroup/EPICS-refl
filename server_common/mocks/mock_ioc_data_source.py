from builtins import object
HIGH_PV_NAMES = ["HIGH_PV1", "HIGH_PV2", "HIGH_PV3"]
HIGH_PVS = [
    [HIGH_PV_NAMES[0], "ai", "HIGH PV 1", "SomeIOC"],
    [HIGH_PV_NAMES[1], "ai", "HIGH PV 2", "SomeIOC"],
    [HIGH_PV_NAMES[2], "ai", "HIGH PV 3", "SomeIOC"]
]

MEDIUM_PV_NAMES = ["MED_PV1", "MED_PV2", "MED_PV3"]
MEDIUM_PVS = [
    [MEDIUM_PV_NAMES[0], "ai", "MED PV 1", "SomeIOC"],
    [MEDIUM_PV_NAMES[1], "ai", "MED PV 2", "SomeIOC"],
    [MEDIUM_PV_NAMES[2], "ai", "MED PV 3", "SomeIOC"]
]

FACILITY_PV_NAMES = ["FAC_PV1", "FAC_PV2", "FAC_PV3"]
FACILITY_PVS = [
    [FACILITY_PV_NAMES[0], "ai", "FACILITY PV 1", "SomeIOC"],
    [FACILITY_PV_NAMES[1], "ai", "FACILITY PV 2", "SomeIOC"],
    [FACILITY_PV_NAMES[2], "ai", "FACILITY PV 3", "SomeIOC"]
]

BL_PVS = ["PARS:BL:FOEMIRROR", "PARS:BL:A1", "PARS:BL:CHOPEN:ANG"]
SAMPLE_PVS = ["PARS:SAMPLE:AOI", "PARS:SAMPLE:GEOMETRY", "PARS:SAMPLE:WIDTH"]
USER_PVS = ["PARS:USER:PV1", "PARS:USER:PV2", "PARS:USER:PV3"]
IOCS = {
    "TESTIOC": {"description": "test ioc", "running": False},
    "SIMPLE1": {"description": "simple ioc 1", "running": False},
    "SIMPLE2": {"description": "simple ioc 2", "running": False}
}


class MockIocDataSource(object):
    def __init__(self):
        self.iocs = IOCS

    def get_iocs_and_descriptions(self):
        return self.iocs

    def get_iocs_and_running_status(self):
        d = []
        for k, v in self.iocs.items():
            d.append((k, v["running"]))
        return d

    def update_ioc_is_running(self, iocname, running):
        self.iocs[iocname]["running"] = running

    def get_interesting_pvs(self, level="", ioc=None):
        pvs = []
        if level == "" or level.lower().startswith('h'):
            pvs.extend(HIGH_PVS)
        if level == "" or level.lower().startswith('m'):
            pvs.extend(MEDIUM_PVS)
        if level == "" or level.lower().startswith('f'):
            pvs.extend(FACILITY_PVS)
        return pvs

    def get_active_pvs(self):
        return HIGH_PV_NAMES

    def get_pars(self, category):
        if category == 'BEAMLINEPAR':
            return BL_PVS
        elif category == 'SAMPLEPAR':
            return SAMPLE_PVS
        elif category == 'USERPAR':
            return USER_PVS