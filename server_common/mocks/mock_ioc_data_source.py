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

LOW_PV_NAMES = ["LOW_PV1", "LOW_PV2", "LOW_PV3"]
LOW_PVS = [
    [LOW_PV_NAMES[0], "ai", "LOW PV 1", "SomeIOC"],
    [LOW_PV_NAMES[1], "ai", "LOW PV 2", "SomeIOC"],
    [LOW_PV_NAMES[2], "ai", "LOW PV 3", "SomeIOC"]
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
        """
        Gets IOC names together with IOC's run status.
        :return: a list of tuples.
        """
        iocs_and_run_status = []
        for ioc_name, ioc_info in self.iocs.iteritems():
            iocs_and_run_status.append((ioc_name, ioc_info["running"]))
        return iocs_and_run_status

    def update_ioc_is_running(self, iocname, running):
        self.iocs[iocname]["running"] = running

    def get_interesting_pvs(self, level="", ioc=None):
        """
        Gets a list of interesting pvs based on their level. The interesting pvs are fake pvs with data defined at the
        beginning of this module.
        Args:
            level (string, optional): The interest level to search for, either High, Medium, Low or Facility. Default to
                                    all interest levels.
            ioc (string, optional): The IOC to search. Default is all IOCs. This argument is not actually used in this
            mock method, but it is used in the method of the real IOCDataSource class, so we need this argument to
            completely imitate the real method.
        Returns:
            list : A list of the PVs that match the search given by level and ioc

        """
        pvs = []

        if level == "":
            pvs = HIGH_PVS + MEDIUM_PVS + LOW_PVS + FACILITY_PVS
        elif level.lower().startswith('h'):
            pvs.extend(HIGH_PVS)
        elif level.lower().startswith('m'):
            pvs.extend(MEDIUM_PVS)
        elif level.lower().startswith('l'):
            pvs.extend(LOW_PVS)
        elif level.lower().startswith('f'):
            pvs.extend(FACILITY_PVS)
        else:
            raise ValueError("Value of level argument can only start with h for high, m for medium, l for low or f for"
                             " facility")

        return pvs

    def get_active_pvs(self):
        """
        Returns names of fake high pvs, because the active pv test compares the result of this method to those fake pvs.
        Returns:
            list : A list of the PVs in running IOCs
        """
        return HIGH_PV_NAMES

    def get_pars(self, category):
        if category == 'BEAMLINEPAR':
            return BL_PVS
        elif category == 'SAMPLEPAR':
            return SAMPLE_PVS
        elif category == 'USERPAR':
            return USER_PVS