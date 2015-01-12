import mysql.connector
from threading import RLock
from server_common.utilities import print_and_log


class MySQLWrapper(object):
    def __init__(self, dbid, procserver, prefix):
        self._dbid = dbid
        self._procserve = procserver
        self._prefix = prefix
        self._running_iocs = list()
        self._running_iocs_lock = RLock()

    def check_db_okay(self):
        conn, curs = self.__open_connection()
        if conn is not None:
            conn.close()

    def __open_connection(self):
        conn = mysql.connector.connect(user="iocdb", password="$iocdb", host="127.0.0.1", database=self._dbid)
        curs = conn.cursor()
        # Check db exists
        curs.execute("SHOW TABLES")
        if len(curs.fetchall()) == 0:
            # Database does not exist - probably means no IOCs have been run (i.e. it is a fresh install)
            raise Exception("PVs database does not exist")
        return conn, curs

    def get_iocs(self):
        conn = None
        try:
            conn, c = self.__open_connection()
            sqlquery = "SELECT iocname FROM iocs"
            c.execute(sqlquery)
            iocs = dict((element[0], dict()) for element in c.fetchall())
        except Exception as err:
            print_and_log("could not get IOCS from database: %s" % err, "ERROR", "DBSVR")
            iocs = dict()
        finally:
            if conn is not None:
                conn.close()
        for ioc in iocs.keys():
            ioc = ioc.encode('ascii', 'replace')
            with self._running_iocs_lock:
                # Create a copy so we don't lock the list for longer than necessary (do we need to do this?)
                running = list(self._running_iocs)
            if ioc in running:
                iocs[ioc]["running"] = True
            else:
                iocs[ioc]["running"] = False
        return iocs

    def get_sample_pars(self):
        conn = None
        values = []
        try:
            conn, c = self.__open_connection()
            sqlquery = ("SELECT pvname FROM pvs"
                        " WHERE (pvname LIKE '%PARS:SAMPLE:%' AND pvname NOT LIKE '%:SEND'"
                        " AND pvname NOT LIKE '%:SP' AND pvname NOT LIKE '%:TYPE')"
                        )
            c.execute(sqlquery)
            # Get as a plain list
            values = [element[0] for element in c.fetchall()]
        except Exception as err:
            print_and_log("could not get sample parameters from database: %s" % err, "ERROR", "DBSVR")
        finally:
            if conn is not None:
                conn.close()
        return values

    def get_beamline_pars(self):
        conn = None
        values = []
        try:
            conn, c = self.__open_connection()
            sqlquery = ("SELECT pvname FROM pvs"
                        " WHERE (pvname LIKE '%PARS:BL:%' AND pvname NOT LIKE '%:SEND'"
                        " AND pvname NOT LIKE '%:SP' AND pvname NOT LIKE '%:TYPE')"
                        )
            c.execute(sqlquery)
            # Get as a plain list
            values = [element[0] for element in c.fetchall()]
        except Exception as err:
            print_and_log("could not get beamline parameters from database: %s" % err, "ERROR", "DBSVR")
        finally:
            if conn is not None:
                conn.close()
        return values

    def update_iocs_status(self):
        # Access the db to get a list of IOCs
        # then check to see if they are currently running
        with self._running_iocs_lock:
            conn = None
            self._running_iocs = list()
            try:
                conn, c = self.__open_connection()
                # Get all the iocnames and whether they are running, but ignore IOCs associated with PSCTRL
                sqlquery = "SELECT iocname, running FROM iocrt WHERE (iocname NOT LIKE 'PSCTRL_%')"
                c.execute(sqlquery)
                rows = c.fetchall()
                for row in rows:
                    # Check to see if running using CA and procserv
                    try:
                        if self._procserve.get_ioc_status(self._prefix, row[0]).upper() == "RUNNING":
                            self._running_iocs.append(row[0])
                            if row[1] == 0:
                                # This should only get called if the IOC failed to tell the DB it started
                                c.execute("UPDATE iocrt SET running=1 WHERE iocname='%s'" % row[0])
                                conn.commit()
                        else:
                            if row[1] == 1:
                                c.execute("UPDATE iocrt SET running=0 WHERE iocname='%s'" % row[0])
                                conn.commit()
                    except Exception as err:
                        # Fail but continue - probably couldn't find procserv for the ioc
                        print_and_log("issue with updating IOC status: %s" % err, "ERROR", "DBSVR")
            except Exception as err:
                print_and_log("issue with updating IOC statuses: %s" % err, "ERROR", "DBSVR")
            finally:
                if conn is not None:
                    conn.close()
                return self._running_iocs

    def get_interesting_pvs(self, level="", ioc=None):
        conn = None
        values = []
        sqlquery = "SELECT pvinfo.pvname, pvs.record_type, pvs.record_desc, pvs.iocname FROM pvinfo"
        sqlquery += " INNER JOIN pvs ON pvs.pvname = pvinfo.pvname"
        where_ioc = ''

        if ioc is not None and ioc != "":
            where_ioc = "AND iocname='%s'" % ioc

        try:
            conn, c = self.__open_connection()
            if level.lower().startswith('h'):
                sqlquery += " WHERE (infoname='INTEREST' AND value LIKE 'H%' {0})".format(where_ioc)
            elif level.lower().startswith('m'):
                sqlquery += " WHERE (infoname='INTEREST' AND value LIKE 'M%' {0})".format(where_ioc)
            else:
                # Try to get everything that has an interest level!
                sqlquery += " WHERE (infoname='INTEREST'  {0})".format(where_ioc)
            c.execute(sqlquery)
            # Get as a plain list of lists
            values = [list(element) for element in c.fetchall()]
            # Convert any bytearrays
            for i, pv in enumerate(values):
                for j, element in enumerate(pv):
                    if type(element) == bytearray:
                        values[i][j] = element.decode("utf-8")
        except Exception as err:
            print_and_log("issue with getting interesting PVs: %s" % err, "ERROR", "DBSVR")
        finally:
            if conn is not None:
                conn.close()
        return values