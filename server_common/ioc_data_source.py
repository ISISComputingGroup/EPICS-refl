from __future__ import print_function, absolute_import, division, unicode_literals

import six

"""
Data source for ioc data
"""
from server_common.mysql_abstraction_layer import DatabaseError
from server_common.utilities import print_and_log

PV_INFO_FIELD_NAME = "info_field"
"""name of the info field on a pv to express its interest level and archive status"""

PV_DESCRIPTION_NAME = "description"
"""name of the description field on a pv"""

GET_PV_INFO_QUERY = """
SELECT s.iocname, p.pvname, lower(p.infoname), p.value
  FROM pvinfo p
  JOIN pvs s ON s.pvname = p.pvname
 WHERE lower(p.infoname) LIKE "log%"
 ORDER BY s.iocname, p.infoname"""
"""Query to return pv info for iocs from the ioc database"""

GET_PVS_WITH_DETAILS = """
    SELECT DISTINCT pvinfo.pvname, pvs.record_type, pvs.record_desc, pvs.iocname
      FROM pvinfo
INNER JOIN pvs ON pvs.pvname = pvinfo.pvname"""

GET_ACTIVE_IOC_INTERESTING_PVS = GET_PVS_WITH_DETAILS + """
     WHERE (pvs.iocname in
       (SELECT iocname
          FROM iocrt
         WHERE running=1)
       AND infoname='INTEREST')"""
"""Select interesting pvs from running active iocs"""

GET_PVS_WITH_TEMPLATED_INTEREST = GET_PVS_WITH_DETAILS + """
WHERE (infoname='INTEREST' AND value='{interest}')"""

GET_PVS_WITH_TEMPLATED_INTEREST_FOR_AN_IOC = GET_PVS_WITH_TEMPLATED_INTEREST + """
AND iocname=%s"""

GET_PVS_WITH_DETAILS_FOR_AN_IOC = GET_PVS_WITH_DETAILS + """
AND iocname=%s"""

GET_PVNAMES_IN_PVCATEGORY = """
  SELECT DISTINCT pvinfo.pvname
             FROM pvinfo
       INNER JOIN pvs ON pvs.pvname = pvinfo.pvname
            WHERE infoname='PVCATEGORY'
              AND value LIKE %s
              AND pvinfo.pvname NOT LIKE '%:SP'"""
"""Get pvnames that are om a PV Category but are not set points"""

GET_IOCS_AND_DESCRIPTIONS = "SELECT iocname, descr FROM iocs"
"""Return all IOC andes and their descriptions"""

GET_IOCS_AND_RUNNING_STATUS = """
  SELECT DISTINCT iocname, running
    FROM iocrt
   WHERE iocname NOT LIKE 'PSCTRL_%'"""
"""Sql query for getting iocnames and their running status"""

UPDATE_IOC_IS_RUNNING = "UPDATE iocrt SET running=%s WHERE iocname=%s"
"""Update whether an ioc is running"""

UPDATE_PV_INFO = "INSERT INTO pvinfo (pvname, infoname, value) VALUES (%s,%s,%s)"
"""Update the pv info"""

INSERT_PV_DETAILS = "INSERT INTO pvs (pvname, record_type, record_desc, iocname) VALUES (%s,%s,%s,%s)"
"""Insert PV details into the pvs table"""

INSERT_IOC_STARTED_DETAILS = "INSERT INTO iocrt (iocname, pid, start_time, stop_time, running, exe_path) " \
                 "VALUES (%s,%s,NOW(),'1970-01-01 00:00:01',1,%s)"
"""Insert details about the start of an IOC"""

DELETE_IOC_RUN_STATE = "DELETE FROM iocrt WHERE iocname=%s"
"""Delete ioc run state"""

DELETE_IOC_PV_DETAILS = "DELETE FROM pvs WHERE iocname=%s"
"""Delete ioc pv details, this cascades to pv info details"""


class IocDataSource(object):
    """
    A source for IOC data from the database
    """
    def __init__(self, mysql_abstraction_layer):
        """
        Constructor.

        Args:
            mysql_abstraction_layer(server_common.mysql_abstraction_layer.AbstratSQLCommands): contact database with sql
        """
        self.mysql_abstraction_layer = mysql_abstraction_layer

    def _query_and_normalise(self, sqlquery, bind_vars=None):
        """
        Executes the given query to the database and converts the data in each row from bytearray to a normal string.
        :param sqlquery: The query to execute.
        :param bind_vars: Any variables to bind to query. Defaults to None.
        :return: A list of lists of strings, representing the data from the table.
        """
        # Get as a plain list of lists
        values = [list(element) for element in self.mysql_abstraction_layer.query(sqlquery, bind_vars)]

        # Convert any bytearrays
        for i, pv in enumerate(values):
            for j, element in enumerate(pv):
                if type(element) == bytearray:
                    values[i][j] = element.decode("utf-8")
        return values

    def get_iocs_and_descriptions(self):
        """
        Gets a list of all the IOCs in the database and their descriptions.

        Returns:
            dict : IOCs and their descriptions
        """
        try:
            ioc_and_description_list = self._query_and_normalise(GET_IOCS_AND_DESCRIPTIONS)
            return dict((element[0], dict(description=element[1])) for element in ioc_and_description_list)
        except Exception as err:
            print_and_log("could not get IOCS from database: %s" % err, "MAJOR", "DBSVR")
            return dict()

    def get_pars(self, category):
        """
        Gets parameters of a particular category from the IOC database of.

        Returns:
            list : A list of the names of PVs associated with the parameter category
        """
        try:
            values = self._query_and_normalise(GET_PVNAMES_IN_PVCATEGORY, ("%{0}%".format(category),))
            return [six.text_type(val[0]) for val in values]
        except Exception as err:
            print_and_log("could not get parameters category %s from database: %s" % (category, err), "MAJOR", "DBSVR")
            return []

    def get_pv_logging_info(self):
        """
        Get pv info for annotations which start with LOG.

        Returns: list of tuples (ioc name, pv name, infoname, value)
        """

        data = self._query_and_normalise(GET_PV_INFO_QUERY)
        pv_logging_info = {}
        for iocname, pvname, infoname, value in data:
            ioc_values = pv_logging_info.get(iocname, [])
            ioc_values.append([pvname, infoname, value])
            pv_logging_info[iocname] = ioc_values

        return pv_logging_info

    def get_interesting_pvs(self, level="", ioc=None):
        """
        Queries the database for PVs based on their interest level and their IOC.

        Args:
            level (string, optional): The interest level to search for, either High, Medium, Low or Facility. Default to
                                    all interest levels.
            ioc (string, optional): The IOC to search. Default is all IOCs.

        Returns:
            list : A list of the PVs that match the search given by level and ioc

        """
        try:
            if level.lower().startswith('h'):
                interest = 'HIGH'
            elif level.lower().startswith('m'):
                interest = 'MEDIUM'
            elif level.lower().startswith('l'):
                interest = 'LOW'
            elif level.lower().startswith('f'):
                interest = 'FACILITY'
            else:
                # Try to get all pvs!
                interest = None

            if ioc is not None and ioc != "":
                bind_vars = (ioc, )
                if interest is not None:
                    sql_query = GET_PVS_WITH_TEMPLATED_INTEREST_FOR_AN_IOC.format(interest=interest)
                else:
                    sql_query = GET_PVS_WITH_DETAILS_FOR_AN_IOC
            else:
                bind_vars = None
                if interest is not None:
                    sql_query = GET_PVS_WITH_TEMPLATED_INTEREST.format(interest=interest)
                else:
                    sql_query = GET_PVS_WITH_DETAILS
            return self._query_and_normalise(sql_query, bind_vars)
        except Exception as err:
            print_and_log("issue with getting interesting PVs: %s" % err, "MAJOR", "DBSVR")
            return []

    def get_active_pvs(self):
        """
        Queries the database for ineresting PVs from active iocs.

        Returns:
            list : A list of the PVs in running IOCs
        """
        try:
            return self._query_and_normalise(GET_ACTIVE_IOC_INTERESTING_PVS)
        except Exception as err:
            print_and_log("issue with getting active PVs: %s" % err, "MAJOR", "DBSVR")
            return []

    def get_iocs_and_running_status(self):
        """
        Get all the iocnames and whether they are running, but ignore IOCs associated with PSCTRL.

        Returns:
            list: iocs and running states
        """
        try:
            return self._query_and_normalise(GET_IOCS_AND_RUNNING_STATUS)
        except Exception as err:
            print_and_log("issue with reading IOC statuses before update: %s" % err, "MAJOR", "DBSVR")
            return []

    def update_ioc_is_running(self, ioc_name, running):
        """
        Update running state in the database.

        Args:
            ioc_name: iocs name
            running: the new running state
        """
        try:
            self.mysql_abstraction_layer.update(UPDATE_IOC_IS_RUNNING, (running, ioc_name))
        except Exception as err:
            print_and_log("Failed to update ioc running state in database ({ioc_name},{running}): {error}"
                          .format(ioc_name=ioc_name, running=running, error=err), "MAJOR", "DBSVR")

    def insert_ioc_start(self, ioc_name, pid, exe_path, pv_database, prefix):
        """
        Insert ioc start information into the database. This does a similar task to pvdump but for python server.
        Args:
            ioc_name: name of the ioc
            pid: process id of the program
            exe_path: executable's path
            pv_database: pv database used to construct the pv. To add a pv info field use entries in the pv for
                PV_INFO_FIELD_NAME.
                For example: {'pv name': {'info_field': {'archive': '', 'INTEREST': 'HIGH'}, 'type': 'float'}}
            prefix: prefix for the pv server
        """
        self._remove_ioc_from_db(ioc_name)
        self._add_ioc_start_to_db(exe_path, ioc_name, pid)

        for pvname, pv in pv_database.items():
            pv_fullname = "{}{}".format(prefix, pvname)
            self._add_pv_to_db(ioc_name, pv, pv_fullname)

            for info_field_name, info_field_value in pv.get(PV_INFO_FIELD_NAME, {}).items():
                self._add_pv_info_to_db(info_field_name, info_field_value, pv_fullname)

    def _add_pv_info_to_db(self, info_field_name, info_field_value, pv_fullname):
        """
        Add pv info to the database.
        Args:
            info_field_name: name of the info field
            info_field_value: value of the info field
            pv_fullname: full pv name with prefix

        Returns: nothing.

        """
        try:
            self.mysql_abstraction_layer.update(UPDATE_PV_INFO, (pv_fullname, info_field_name, info_field_value))
        except Exception as err:
            print_and_log("Failed to insert pv info for pv '{pvname}' with name '{name}' and value "
                          "'{value}': {error}".format(pvname=pv_fullname, name=info_field_name,
                                                      value=info_field_value, error=err), "MAJOR", "DBSVR")

    def _add_pv_to_db(self, ioc_name, pv, pv_fullname):
        """
        Add a pv to the database
        Args:
            ioc_name: name of the ioc
            pv: pv information
            pv_fullname: pv's full name
        """
        try:
            pv_type = pv.get('type', "float")
            description = pv.get(PV_DESCRIPTION_NAME, "")
            self.mysql_abstraction_layer.update(INSERT_PV_DETAILS, (pv_fullname, pv_type, description, ioc_name))
        except DatabaseError as err:
            print_and_log("Failed to insert pv data for pv '{pvname}' with contents '{pv}': {error}"
                          .format(ioc_name=ioc_name, pvname=pv_fullname, pv=pv, error=err), "MAJOR", "DBSVR")

    def _add_ioc_start_to_db(self, exe_path, ioc_name, pid):
        """
        Add the ioc start to the database
        Args:
            exe_path: the path to the executab;e
            ioc_name: the ioc name
            pid: the process id
        """
        try:

            self.mysql_abstraction_layer.update(INSERT_IOC_STARTED_DETAILS, (ioc_name, pid, exe_path))
        except DatabaseError as err:
            print_and_log("Failed to insert ioc into database ({ioc_name},{pid},{exepath}): {error}"
                          .format(ioc_name=ioc_name, pid=pid, exepath=exe_path, error=err), "MAJOR", "DBSVR")

    def _remove_ioc_from_db(self, ioc_name):
        """
        Remove the ioc data from the database
        Args:
            ioc_name: name of the ioc
        """
        try:
            self.mysql_abstraction_layer.update(DELETE_IOC_RUN_STATE, (ioc_name,))
        except DatabaseError as err:
            print_and_log("Failed to delete ioc, '{ioc_name}', from iocrt: {error}"
                          .format(ioc_name=ioc_name, error=err), "MAJOR", "DBSVR")
        try:
            self.mysql_abstraction_layer.update(DELETE_IOC_PV_DETAILS, (ioc_name,))
        except DatabaseError as err:
            print_and_log("Failed to delete ioc, '{ioc_name}', from pvs: {error}"
                          .format(ioc_name=ioc_name, error=err), "MAJOR", "DBSVR")
