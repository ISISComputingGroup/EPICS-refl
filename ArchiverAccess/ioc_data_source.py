

GET_PV_INFO_QUERY = """
SELECT s.iocname, p.pvname, p.infoname, p.value 
  FROM pvinfo p 
  JOIN pvs s ON s.pvname = p.pvname 
 WHERE p.infoname LIKE "LOG%" 
 ORDER BY s.iocname, p.infoname"""
"""Query to return pv info for iocs from the ioc database"""

class IocDataSource(object):
    def __init__(self, mysql_abstraction_layer):
        self.mysql_abstraction_layer = mysql_abstraction_layer

    def get_pv_logging_info(self):

        data = self.mysql_abstraction_layer.query(GET_PV_INFO_QUERY)
        pv_logging_info = {}
        for iocname, pvname, infoname, value in data:
            ioc_values = pv_logging_info.get(iocname, [])
            ioc_values.append((pvname, infoname, value))
            pv_logging_info[iocname] = ioc_values

        return pv_logging_info
