'''
This file is part of the ISIS IBEX application.
Copyright (C) 2012-2015 Science & Technology Facilities Council.
All rights reserved.

This program is distributed in the hope that it will be useful.
This program and the accompanying materials are made available under the
terms of the Eclipse Public License v1.0 which accompanies this distribution.
EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.

You should have received a copy of the Eclipse Public License v1.0
along with this program; if not, you can obtain a copy from
https://www.eclipse.org/org/documents/epl-v10.php or 
http://opensource.org/licenses/eclipse-1.0.php
'''
import sys
import os
basedir = os.path.abspath(".")
print basedir
sys.path.append(basedir)

from server_common.channel_access import caget, caput
from BlockServer.core.macros import MACROS, BLOCKSERVER_PREFIX, BLOCK_PREFIX
from server_common.utilities import compress_and_hex, dehex_and_decompress, print_and_log, convert_to_json
import json

TEST_CONFIG = {"iocs":
                 [{"simlevel": "devsim", "autostart": True, "restart": False,
                 "macros": [],
                 "pvsets": [],
                 "pvs": [],
                 "name": "SIMPLE", "component": None},
                 ],
              "blocks":
                       [{"name": "testblock1", "local": True,
                       "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                        {"name": "testblock2", "local": True,
                        "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                        {"name": "testblock3", "local": True,
                        "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "component": None, "visible": True}
                       ],
              "components":
                           [],
              "groups":
                       [{"blocks": ["testblock1"], "name": "Group1", "component": None},
                        {"blocks": ["testblock2"], "name": "Group2", "component": None},
                        {"blocks": ["testblock3"], "name": "NONE", "component": None}],
              "name": "",
              "description": "A test configuration",
              "history": ["2015-02-16"]
             }


TEST_COMP = {"iocs":
                 [],
              "blocks":
                       [{"name": "comptestblock1", "local": True,
                       "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                        {"name": "comptestblock2", "local": True,
                        "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "component": None, "visible": True},
                        {"name": "comptestblock3", "local": True,
                        "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "component": None, "visible": True}
                       ],
              "components":
                           [],
              "groups":
                       [{"blocks": ["comptestblock1"], "name": "CompGroup1", "component": None},
                        {"blocks": ["comptestblock2"], "name": "Group2", "component": None},
                        {"blocks": ["comptestblock3"], "name": "NONE", "component": None}],
              "name": "",
              "description": "A test component",
              "history": ["2015-02-16"]
             }


def get_and_decode(pv):
    raw = caget(pv, True)
    js = dehex_and_decompress(raw)
    ans = json.loads(js)
    return ans


def put_and_decode_ans(pv, value):
    caput(pv, compress_and_hex(value), wait=True)
    raw = caget(pv, True)
    js = dehex_and_decompress(raw)
    ans = json.loads(js)
    return ans


def get_curr_config_details():
    pv = BLOCKSERVER_PREFIX + "GET_CURR_CONFIG_DETAILS"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_blank_config():
    pv = BLOCKSERVER_PREFIX + "BLANK_CONFIG"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_blocknames():
    pv = BLOCKSERVER_PREFIX + "BLOCKNAMES"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_groups():
    pv = BLOCKSERVER_PREFIX + "GROUPS"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_available_configs():
    pv = BLOCKSERVER_PREFIX + "CONFIGS"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_available_comps():
    pv = BLOCKSERVER_PREFIX + "COMPS"
    ans = get_and_decode(pv)
    print ans
    return ans


def get_server_status():
    pv = BLOCKSERVER_PREFIX + "SERVER_STATUS"
    ans = get_and_decode(pv)
    print ans
    return ans


def load_config(name):
    pv = BLOCKSERVER_PREFIX + "LOAD_CONFIG"
    ans = put_and_decode_ans(pv, name)
    print ans
    return ans


def save_active_config(name):
    pv = BLOCKSERVER_PREFIX + "SAVE_CONFIG"
    ans = put_and_decode_ans(pv, name)
    print ans
    return ans


def save_inactive_config(name, data):
    pv = BLOCKSERVER_PREFIX + "SAVE_NEW_CONFIG"
    # Insert the name into the data
    data["name"] = name
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def save_inactive_config(name, data):
    pv = BLOCKSERVER_PREFIX + "SAVE_NEW_CONFIG"
    # Insert the name into the data
    data["name"] = name
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def save_active_as_component(name, data):
    pv = BLOCKSERVER_PREFIX + "SAVE_NEW_COMPONENT"
    # Insert the name into the data
    data["name"] = name
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def save_inactive_as_component(name, data):
    pv = BLOCKSERVER_PREFIX + "SAVE_NEW_COMPONENT"
    # Insert the name into the data
    data["name"] = name
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def start_ioc(name):
    pv = BLOCKSERVER_PREFIX + "START_IOCS"
    data = [name]
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def stop_ioc(name):
    pv = BLOCKSERVER_PREFIX + "STOP_IOCS"
    data = [name]
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def restart_ioc(name):
    pv = BLOCKSERVER_PREFIX + "RESTART_IOCS"
    data = [name]
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def delete_config(name):
    pv = BLOCKSERVER_PREFIX + "DELETE_CONFIGS"
    data = [name]
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def delete_comp(name):
    pv = BLOCKSERVER_PREFIX + "DELETE_COMPONENTS"
    data = [name]
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans


def set_curr_config_details(name, data):
    pv = BLOCKSERVER_PREFIX + "SET_CURR_CONFIG_DETAILS"
    # Insert the name into the data
    data["name"] = name
    ans = put_and_decode_ans(pv, json.dumps(data))
    print ans
    return ans
    

def get_runcontrol_out():
    pv = BLOCKSERVER_PREFIX + "GET_RC_OUT"
    ans = get_and_decode(pv)
    print ans
    return ans

    
def get_runcontrol_pars():
    pv = BLOCKSERVER_PREFIX + "GET_RC_PARS"
    ans = get_and_decode(pv)
    print ans
    return ans