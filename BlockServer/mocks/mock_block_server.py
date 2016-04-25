#This file is part of the ISIS IBEX application.
#Copyright (C) 2012-2016 Science & Technology Facilities Council.
#All rights reserved.
#
#This program is distributed in the hope that it will be useful.
#This program and the accompanying materials are made available under the
#terms of the Eclipse Public License v1.0 which accompanies this distribution.
#EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
#AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
#OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
#You should have received a copy of the Eclipse Public License v1.0
#along with this program; if not, you can obtain a copy from
#https://www.eclipse.org/org/documents/epl-v10.php or 
#http://opensource.org/licenses/eclipse-1.0.php

from threading import RLock


class MockBlockServer(object):
    def __init__(self):
        self._comps = list()
        self._confs = list()
        self._pvs = dict()
        self.monitor_lock = RLock()

    def set_config_list(self, cl):
        self._config_list = cl

    def get_confs(self):
        return self._confs

    def update_config_monitors(self):
        self._confs = self._config_list.get_configs()

    def get_comps(self):
        return self._comps

    def update_comp_monitor(self):
        self._comps = self._config_list.get_components()

    def update_synoptic_monitor(self):
        pass

    def load_last_config(self):
        pass

    def does_pv_exist(self, name):
        return name in self._pvs

    def delete_pv_from_db(self, name):
        del self._pvs[name]

    def add_string_pv_to_db(self, name, count=1000):
        print name
        self._pvs[name] = ""

    def setParam(self, name, data):
        self._pvs[name] = data

    def updatePVs(self):
        pass
