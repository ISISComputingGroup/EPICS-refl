import unittest
import mysql.connector
from mysql_wrapper import MySQLWrapper as dbwrap
from mocks.mock_procserv_utils import MockProcServWrapper

TEST_DB = 'test_iocdb'
HIGH_PV_NAMES = list()
MEDIUM_PV_NAMES = list()
BL_PVS = ["PARS:BL:FOEMIRROR", "PARS:BL:A1", "PARS:BL:CHOPEN:ANG"]
SAMPLE_PVS = ["PARS:SAMPLE:AOI", "PARS:SAMPLE:GEOMETRY", "PARS:SAMPLE:WIDTH"]


def generate_fake_db(iocdb):
    cnx = mysql.connector.connect(user="root", password="isis@instdb99", host="127.0.0.1")
    cursor = cnx.cursor()
    #create the user and the database
    sql = []
    sql.append("GRANT SELECT,UPDATE ON %s.* TO test@localhost IDENTIFIED BY '$test'" % iocdb)
    sql.append("GRANT SELECT,UPDATE ON %s.* TO test@'%%' IDENTIFIED BY '$test'" % iocdb)
    sql.append("FLUSH PRIVILEGES")
    sql.append("DROP DATABASE IF EXISTS %s" % iocdb)
    sql.append("CREATE DATABASE %s" % iocdb)
    for line in sql:
        cursor.execute(line)
    cursor.close()
    cnx.close
    #Move the connection to the appropriate database for ease of table creation
    cnx = mysql.connector.connect(user="test", password="$test", host="127.0.0.1", database = iocdb)
    cursor = cnx.cursor()
    #Drop, create and fill the tables
    sql = []
    sql.append("DROP TABLE IF EXISTS iocs")
    sql.append("DROP TABLE IF EXISTS pvs")
    sql.append("DROP TABLE IF EXISTS pvinfo")
    sql.append("DROP TABLE IF EXISTS iocrt")
    sql.append(
        """
        CREATE TABLE IF NOT EXISTS iocs (
            iocname VARCHAR(100) PRIMARY KEY NOT NULL COMMENT 'IOC Name',
	        dir VARCHAR(100) COMMENT 'IOC boot directory',
	        consoleport INT COMMENT 'procServ console port',
	        logport INT COMMENT 'procServ read-only log port',
	        exe VARCHAR(100) COMMENT 'procServ file to execute',
	        cmd VARCHAR(100) COMMENT 'procServ command argument',
	        UNIQUE(consoleport),
	        UNIQUE(logport)
        )
        """
    )
    sql.append(
        """
        CREATE TABLE IF NOT EXISTS pvs(
            pvname VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_bin PRIMARY KEY NOT NULL,
	        record_type VARCHAR(100),
	        record_desc VARCHAR(100),
	        iocname VARCHAR(100) NOT NULL,
	        FOREIGN KEY(iocname) REFERENCES iocs(iocname) ON DELETE CASCADE ON UPDATE CASCADE
	    )
	    """
    )
    sql.append(
        """
        CREATE TABLE IF NOT EXISTS pvinfo(
            pvname VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
	        infoname VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL COMMENT 'DB info field name',
	        value VARCHAR(100),
	        FOREIGN KEY(pvname) REFERENCES pvs(pvname) ON DELETE CASCADE ON UPDATE CASCADE,
	        PRIMARY KEY(pvname, infoname)
        )
        """
    )
    sql.append(
        """
        CREATE TABLE IF NOT EXISTS iocrt(
            iocname VARCHAR(100) PRIMARY KEY NOT NULL,
	        pid INT COMMENT 'IOC process id',
	        start_time TIMESTAMP COMMENT 'Time IOC last started',
	        stop_time TIMESTAMP COMMENT 'Time IOC last stopped',
	        running INT COMMENT '1 if running, 0 if stopped',
	        exe_path VARCHAR(100) COMMENT 'path to IOC executable',
	        FOREIGN KEY(iocname) REFERENCES iocs(iocname) ON DELETE CASCADE ON UPDATE CASCADE
        )
        """
    )
    for line in sql:
        cursor.execute(line)
    sql = []
    count = 0
    for iocname in ['SIMPLE1', "SIMPLE2", "TESTIOC"]:
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
    # Add sample and beamline parameters
    sql.append("""INSERT INTO `%s`.`iocs` (`iocname`, `dir`, `consoleport`, `logport`, `exe`, `cmd`) VALUES ('%s','%s','%s','%s','%s','%s')""" % (iocdb,'INSTETC', 'fake_dir', count, count, 'fake_exe', 'fake_cmd'))
    row = ("INSTETC", 'fake_dir', count, count, 'fake_exe', 'fake_cmd')
    pvnames = list(SAMPLE_PVS)
    pvnames.extend(BL_PVS)
    for pv in pvnames:
        MEDIUM_PV_NAMES.append(pv)
        sql.append("""INSERT INTO `%s`.`pvs` (`pvname`, `record_type`, `record_desc`, `iocname`) VALUES ('%s','%s','%s','%s')""" % (iocdb, pv, 'ai', 'Fake pv for testing', 'INSTETC'))
        # Add interesting PVs
        sql.append("""INSERT INTO `%s`.`pvinfo` (`pvname`, `infoname`, `value`) VALUES ('%s','%s','%s')""" % (iocdb, pv, 'INTEREST', 'MEDIUM'))
    for line in sql:
        cursor.execute(line)
    cnx.commit()
    cursor.close()
    cnx.close

generate_fake_db(TEST_DB)

class TestMySQLWrapperSequence(unittest.TestCase):
    def setUp(self):
        self.prefix = ""
        self.wrapper = dbwrap(TEST_DB, MockProcServWrapper(), self.prefix)

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
        self.wrapper = dbwrap(TEST_DB, ps, self.prefix)

        running = self.wrapper.update_iocs_status()
        self.assertEqual(len(running), 2)

    def test_check_db_okay(self):
        try:
            self.wrapper.check_db_okay()
        except:
            self.fail("check_db_okay throw an exception")

    def test_check_db_okay_fails(self):
        self.wrapper = dbwrap("not_a_db", MockProcServWrapper(), self.prefix)
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