import unittest
import mysql.connector
from ioc_data import IOCData
from mocks.mock_procserv_utils import MockProcServWrapper

TEST_DB = 'test_iocdb'
HIGH_PV_NAMES = list()
MEDIUM_PV_NAMES = list()
FACILITY_PV_NAMES = ["AC:EPB1:BEAM:CURR"]
BL_PVS = ["PARS:BL:FOEMIRROR", "PARS:BL:A1", "PARS:BL:CHOPEN:ANG"]
SAMPLE_PVS = ["PARS:SAMPLE:AOI", "PARS:SAMPLE:GEOMETRY", "PARS:SAMPLE:WIDTH"]


def generate_fake_db(iocdb):
    import sys
    import shutil
    import os
    import fileinput
    #create the schema file
    schemapath = os.path.join(os.environ['EPICS_KIT_ROOT'],'iocstartup','iocdb_mysql_schema.txt')
    testpath = os.path.join(os.environ['EPICS_KIT_ROOT'],'iocstartup','test_iocdb_mysql_schema.txt')
    schemafile = open(schemapath, 'r')
    testfile = open(testpath, 'w')
    for line in schemafile:
        if not line.isspace():
            if line[:3] == "-- " or line[0] == "#" or 'GRANT' in line or 'FLUSH' in line:
                pass
            else:
                testfile.write(line.replace('iocdb',iocdb))
    schemafile.close()
    testfile.close()
    #Note that the account below is the test account, and is only available on localhost
    cnx = mysql.connector.connect(user="isis_test", password="test@isis99", host="localhost")
    cursor = cnx.cursor()
    testfile = open(testpath, 'r')
    sql = testfile.read()
    for result in cursor.execute(sql,multi = True):
        pass
    cnx.commit()
    cursor.close()
    cnx.disconnect()
    #Move the connection to the appropriate database for ease of table creation
    cnx = mysql.connector.connect(user=iocdb, password="$" + iocdb, host="127.0.0.1", database = iocdb)
    cursor = cnx.cursor()
    #Populate the tables for testing
    sql = []
    count = 0
    for iocname in ['SIMPLE1', "SIMPLE2", "TESTIOC", "STOPDIOC"]:
        # Populate iocs
        sql.append("""INSERT INTO `%s`.`iocs` (`iocname`, `dir`, `consoleport`, `logport`, `exe`, `cmd`) VALUES ('%s','%s','%s','%s','%s','%s')""" % (iocdb,iocname, 'fake_dir', count, count, 'fake_exe', 'fake_cmd'))
        # Populate iocsrt
        sql.append("""INSERT INTO `%s`.`iocrt` (`iocname`, `pid`, `start_time`, `stop_time`, `running`, `exe_path`) VALUES ('%s','%s','%s','%s','%s','%s')""" % (iocdb,iocname,count,'0000-00-00 00:00:00','0000-00-00 00:00:00', 1, 'fake exe path'))
        count += 1
        # Populate pvs and pvinfo
        pvnames = ["%s:VALUE1" % iocname, "%s:VALUE2" % iocname]
        for pv in pvnames:
            sql.append("""INSERT INTO `%s`.`pvs` (`pvname`, `record_type`, `record_desc`, `iocname`) VALUES ('%s','%s','%s','%s')""" % (iocdb, pv, 'ai', 'Fake pv for testing', iocname))
            # Add interesting PVs
            HIGH_PV_NAMES.append(pv)
            sql.append("""INSERT INTO `%s`.`pvinfo` (`pvname`, `infoname`, `value`) VALUES ('%s','%s','%s')""" % (iocdb, pv, 'INTEREST', 'HIGH'))
        # Add procserve
        pvnames = ["%s:START" % iocname, "%s:STOP" % iocname, "%s:RESTART" % iocname, "%s:STATUS" % iocname]
        for pv in pvnames:
            sql.append("""INSERT INTO `%s`.`pvs` (`pvname`, `record_type`, `record_desc`, `iocname`) VALUES ('%s','%s','%s','%s')""" % (iocdb, pv, 'ai', 'Fake procserv pv for testing', iocname))
    # Alter STOPDIOC to be inactive to test PVS:ACTIVE type tests
    sql.append("""UPDATE %s.iocrt SET running=0 WHERE iocname='STOPDIOC'""" % iocdb)
    # Add sample and beamline parameters
    sql.append("""INSERT INTO `%s`.`iocs` (`iocname`, `dir`, `consoleport`, `logport`, `exe`, `cmd`) VALUES ('%s','%s','%s','%s','%s','%s')""" % (iocdb,'INSTETC', 'fake_dir', count, count, 'fake_exe', 'fake_cmd'))
    pvnames = list(SAMPLE_PVS)
    pvnames.extend(BL_PVS)
    for pv in pvnames:
        MEDIUM_PV_NAMES.append(pv)
        sql.append("""INSERT INTO `%s`.`pvs` (`pvname`, `record_type`, `record_desc`, `iocname`) VALUES ('%s','%s','%s','%s')""" % (iocdb, pv, 'ai', 'Fake pv for testing', 'INSTETC'))
        # Add interesting PVs
        sql.append("""INSERT INTO `%s`.`pvinfo` (`pvname`, `infoname`, `value`) VALUES ('%s','%s','%s')""" % (iocdb, pv, 'INTEREST', 'MEDIUM'))
    pvnames = list(FACILITY_PV_NAMES)
    for pv in pvnames:
        sql.append("""INSERT INTO `%s`.`pvs` (`pvname`, `record_type`, `record_desc`, `iocname`) VALUES ('%s','%s','%s','%s')""" % (iocdb, pv, 'ai', 'Fake pv for testing', 'INSTETC'))
        # Add interesting PVs
        sql.append("""INSERT INTO `%s`.`pvinfo` (`pvname`, `infoname`, `value`) VALUES ('%s','%s','%s')""" % (iocdb, pv, 'INTEREST', 'FACILITY'))
    for line in sql:
        cursor.execute(line)
    cnx.commit()
    cursor.close()
    cnx.disconnect()

generate_fake_db(TEST_DB)

class TestMySQLWrapperSequence(unittest.TestCase):
    def setUp(self):
        self.prefix = ""
        self.wrapper = IOCData(TEST_DB, MockProcServWrapper(), self.prefix)

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
        self.wrapper = IOCData(TEST_DB, ps, self.prefix)

        running = self.wrapper.update_iocs_status()
        self.assertEqual(len(running), 2)

    def test_check_db_okay(self):
        try:
            self.wrapper.check_db_okay()
        except:
            self.fail("check_db_okay throw an exception")

    def test_check_db_okay_fails(self):
        self.wrapper = IOCData("not_a_db", MockProcServWrapper(), self.prefix)
        self.assertRaises(Exception, self.wrapper.check_db_okay)

    def test_get_interesting_pvs_all(self):
        # Get all PVs
        pvs = self.wrapper.get_interesting_pvs()
        for pv in pvs:
            self.assertTrue(pv[0] in MEDIUM_PV_NAMES or pv[0] in HIGH_PV_NAMES or pv[0] in FACILITY_PV_NAMES)

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

    def test_get_interesting_pvs_facility(self):
        # Get all PVs
        pvs = self.wrapper.get_interesting_pvs("FACILITY")
        for pv in pvs:
            self.assertTrue(pv[0] in FACILITY_PV_NAMES)

    def test_get_active_pvs_high(self):
        # Get all Active PVs
        pvs = self.wrapper.get_active_pvs()
        for pv in pvs:
            self.assertTrue("STOPDIOC" not in pv[0])

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
