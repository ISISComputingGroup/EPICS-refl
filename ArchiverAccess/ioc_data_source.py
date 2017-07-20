# This file is part of the ISIS IBEX application.
# Copyright (C) 2017 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Module for reading data from the ioc database.
"""


GET_PV_INFO_QUERY = """
SELECT s.iocname, p.pvname, p.infoname, p.value 
  FROM pvinfo p 
  JOIN pvs s ON s.pvname = p.pvname 
 WHERE p.infoname LIKE "LOG%" 
 ORDER BY s.iocname, p.infoname"""
"""Query to return pv info for iocs from the ioc database"""


class IocDataSource(object):
    """
    A source for ioc data
    """
    def __init__(self, mysql_abstraction_layer):
        self.mysql_abstraction_layer = mysql_abstraction_layer

    def get_pv_logging_info(self):

        data = self.mysql_abstraction_layer.query(GET_PV_INFO_QUERY)
        pv_logging_info = {}
        for iocname, pvname, infoname, value in data:
            ioc_values = pv_logging_info.get(str(iocname), [])
            ioc_values.append((str(pvname), str(infoname), str(value)))
            pv_logging_info[iocname] = ioc_values

        return pv_logging_info
