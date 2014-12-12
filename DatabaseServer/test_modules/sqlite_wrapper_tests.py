import unittest
import sqlite3
from sqlite_wrapper import SqliteWrapper
from mocks.mock_procserv_utils import MockProcServWrapper

TEST_DB = 'test_db.sq3'
HIGH_PV_NAMES = list()
MEDIUM_PV_NAMES = list()
BL_PVS = ["PARS:BL:FOEMIRROR", "PARS:BL:A1", "PARS:BL:CHOPEN:ANG"]
SAMPLE_PVS = ["PARS:SAMPLE:AOI", "PARS:SAMPLE:GEOMETRY", "PARS:SAMPLE:WIDTH"]


def generate_fake_db(iocdb):
    import sys
    sys.path.append("../../../")
    from build_ioc_startups import create_iocs_database
    # Create database with empty table
    create_iocs_database(iocdb)
    # Populate
    conn = sqlite3.connect(iocdb)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    count = 0
    for iocname in ['SIMPLE1', "SIMPLE2", "TESTIOC"]:
        # Populate iocs
        row = (iocname, 'fake_dir', count, count, 'fake_exe', 'fake_cmd')
        c.execute("INSERT INTO iocs VALUES (?,?,?,?,?,?)", row)
        # Populate iocsrt
        # Columns = iocname, pid, starttime, stoptime, running, exe-path
        row = (iocname, count, 0, 0, 1, "fake exe path")
        c.execute("INSERT INTO iocrt VALUES (?,?,?,?,?,?)", row)
        count += 1
        # Populate pvs and pvinfo
        pvnames = ["%s:VALUE1" % iocname, "%s:VALUE2" % iocname]
        for pv in pvnames:
            # Columns = pvname, record_type, record_desc, iocname
            row = (pv, 'ai', "Fake pv for testing", iocname)
            c.execute("INSERT INTO pvs VALUES (?,?,?,?)", row)
            # Add interesting PVs
            HIGH_PV_NAMES.append(pv)
            row = (pv, 'INTEREST', "HIGH")
            c.execute("INSERT INTO pvinfo VALUES (?,?,?)", row)
        # Add procserve
        pvnames = ["%s:START" % iocname, "%s:STOP" % iocname, "%s:RESTART" % iocname, "%s:STATUS" % iocname]
        for pv in pvnames:
            # Columns = pvname, record_type, record_desc, iocname
            row = (pv, 'ai', "Fake procserv pv for testing", iocname)
            c.execute("INSERT INTO pvs VALUES (?,?,?,?)", row)
    # Add sample and beamline parameters
    row = ("INSTETC", 'fake_dir', count, count, 'fake_exe', 'fake_cmd')
    c.execute("INSERT INTO iocs VALUES (?,?,?,?,?,?)", row)
    pvnames = list(SAMPLE_PVS)
    pvnames.extend(BL_PVS)
    for pv in pvnames:
        # Columns = pvname, record_type, record_desc, iocname
        MEDIUM_PV_NAMES.append(pv)
        row = (pv, 'ai', "Fake pv for testing", "INSTETC")
        c.execute("INSERT INTO pvs VALUES (?,?,?,?)", row)
        # Add interesting PVs
        row = (pv, 'INTEREST', "MEDIUM")
        c.execute("INSERT INTO pvinfo VALUES (?,?,?)", row)
    conn.commit()
    conn.close()

generate_fake_db(TEST_DB)


class TestSqliteWrapperSequence(unittest.TestCase):
    def setUp(self):
        self.prefix = ""
        self.wrapper = SqliteWrapper(TEST_DB, MockProcServWrapper(), self.prefix)

    def test_get_iocs(self):
        iocs = self.wrapper.get_iocs()
        self.assertEqual(iocs["TESTIOC"]["running"], False)
        self.assertEqual(iocs["SIMPLE1"]["running"], False)
        self.assertEqual(iocs["SIMPLE2"]["running"], False)

    def test_update_iocs_status(self):
        running = self.wrapper.update_iocs_status()
        self.assertEqual(len(running), 0)

        # Start some IOCs up
        ps = MockProcServWrapper()
        ps.start_ioc(self.prefix, "SIMPLE1")
        ps.start_ioc(self.prefix, "SIMPLE2")
        self.wrapper = SqliteWrapper(TEST_DB, ps, self.prefix)

        running = self.wrapper.update_iocs_status()
        self.assertEqual(len(running), 2)

    def test_check_db_okay(self):
        try:
            self.wrapper.check_db_okay()
        except:
            self.fail("check_db_okay throw an exception")

    def test_check_db_okay_fails(self):
        self.wrapper = SqliteWrapper("not_a_db", MockProcServWrapper(), self.prefix)
        self.assertRaises(Exception, self.wrapper.check_db_okay)

    def test_get_interesting_pvs_all(self):
        # Get all PVs
        pvs = self.wrapper.get_interesting_pvs()
        for pv in pvs:
            self.assertTrue(pv[0] in MEDIUM_PV_NAMES or pv[0] in HIGH_PV_NAMES)

    def test_get_interesting_pvs_high(self):
        # Get all PVs
        pvs = self.wrapper.get_interesting_pvs("HIGH")
        for pv in pvs:
            self.assertTrue(pv[0] in HIGH_PV_NAMES)

    def test_get_interesting_pvs_medium(self):
        # Get all PVs
        pvs = self.wrapper.get_interesting_pvs("MEDIUM")
        for pv in pvs:
            self.assertTrue(pv[0] in MEDIUM_PV_NAMES)

    def test_get_beamline_pars(self):
        pars = self.wrapper.get_beamline_pars()
        self.assertEqual(len(pars), len(BL_PVS))
        for n in BL_PVS:
            self.assertTrue(n in pars)

    def test_get_sample_pars(self):
        pars = self.wrapper.get_sample_pars()
        self.assertEqual(len(pars), len(SAMPLE_PVS))
        for n in SAMPLE_PVS:
            self.assertTrue(n in pars)

