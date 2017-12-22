from server_common.utilities import print_and_log


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


class IocDataSource(object):
    """
    A source for IOC data from the database
    """
    def __init__(self, mysql_abstraction_layer):
        """
        Constructor.

        Args:
            mysql_abstraction_layer: contact database with sql
        """
        self.mysql_abstraction_layer = mysql_abstraction_layer

    def _query_and_normalise(self, sqlquery, bind_vars=None):
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
            return [str(val[0]) for val in values]
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
            level (string, optional): The interest level to search for, either High, Medium or Facility. Default to
                                    all interest levels
            ioc (string, optional): The IOC to search. Default is all IOCs.

        Returns:
            list : A list of the PVs that match the search given by level and ioc

        """
        try:
            if level.lower().startswith('h'):
                interest = 'HIGH'
            elif level.lower().startswith('m'):
                interest = 'MEDIUM'
            elif level.lower().startswith('f'):
                interest = 'FACILITY'
            else:
                # Try to get all pvs!
                interest = None

            if ioc is not None and ioc != "":
                bind_vars = (ioc, )
                if interest is not None:
                    sqlquery = GET_PVS_WITH_TEMPLATED_INTEREST_FOR_AN_IOC.format(interest=interest)
                else:
                    sqlquery = GET_PVS_WITH_DETAILS_FOR_AN_IOC
            else:
                bind_vars = None
                if interest is not None:
                    sqlquery = GET_PVS_WITH_TEMPLATED_INTEREST.format(interest=interest)
                else:
                    sqlquery = GET_PVS_WITH_DETAILS
            return self._query_and_normalise(sqlquery, bind_vars)
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
            self.mysql_abstraction_layer.update("UPDATE iocrt SET running=%s WHERE iocname=%s", (running, ioc_name))
        except Exception as err:
            print_and_log("Failed to update ioc running state in database ({ioc_name},{running}): {error}"
                          .format(ioc_name=ioc_name, running=running, error=err), "MAJOR", "DBSVR")
