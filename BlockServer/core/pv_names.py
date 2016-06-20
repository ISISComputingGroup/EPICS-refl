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

import os

from BlockServer.core.macros import BLOCKSERVER


class DbNames:
    """Holds and manages blockserver PV names
    """

    @staticmethod
    def prepend_blockserver(base_name):
        return BLOCKSERVER + base_name

    BLOCKNAMES = prepend_blockserver('BLOCKNAMES')
    BLOCK_DETAILS = prepend_blockserver('BLOCK_DETAILS')
    GROUPS = prepend_blockserver('GROUPS')
    COMPS = prepend_blockserver('COMPS')
    LOAD_CONFIG = prepend_blockserver('LOAD_CONFIG')
    SAVE_CONFIG = prepend_blockserver('SAVE_CONFIG')
    CLEAR_CONFIG = prepend_blockserver('CLEAR_CONFIG')
    START_IOCS = prepend_blockserver('START_IOCS')
    STOP_IOCS = prepend_blockserver('STOP_IOCS')
    RESTART_IOCS = prepend_blockserver('RESTART_IOCS')
    CONFIGS = prepend_blockserver('CONFIGS')
    GET_RC_OUT = prepend_blockserver('GET_RC_OUT')
    GET_RC_PARS = prepend_blockserver('GET_RC_PARS')
    SET_RC_PARS = prepend_blockserver('SET_RC_PARS')
    GET_CURR_CONFIG_DETAILS = prepend_blockserver('GET_CURR_CONFIG_DETAILS')
    SET_CURR_CONFIG_DETAILS = prepend_blockserver('SET_CURR_CONFIG_DETAILS')
    SAVE_NEW_CONFIG = prepend_blockserver('SAVE_NEW_CONFIG')
    SAVE_NEW_COMPONENT = prepend_blockserver('SAVE_NEW_COMPONENT')
    SERVER_STATUS = prepend_blockserver('SERVER_STATUS')
    DELETE_CONFIGS = prepend_blockserver('DELETE_CONFIGS')
    DELETE_COMPONENTS = prepend_blockserver('DELETE_COMPONENTS')
    BLANK_CONFIG = prepend_blockserver('BLANK_CONFIG')
    CURR_CONFIG_CHANGED = prepend_blockserver('CURR_CONFIG_CHANGED')
    ACK_CURR_CHANGED = prepend_blockserver('ACK_CURR_CHANGED')
    BUMPSTRIP_AVAILABLE = prepend_blockserver('BUMPSTRIP_AVAILABLE')
    BUMPSTRIP_AVAILABLE_SP = prepend_blockserver('BUMPSTRIP_AVAILABLE:SP')
    SET_SCREENS = prepend_blockserver('SET_SCREENS')


class SynopticsPVNames:
    """Holds and manages the synoptic PV names
    """

    @staticmethod
    def prepend_synoptics(base_name):
        return "SYNOPTICS:" + base_name

    SYNOPTICS_NAMES = prepend_synoptics('NAMES')
    SYNOPTICS_GET_DEFAULT = prepend_synoptics('GET_DEFAULT')
    SYNOPTICS_BLANK_GET = prepend_synoptics('__BLANK__:GET')
    SYNOPTICS_SET_DETAILS = prepend_synoptics('SET_DETAILS')
    SYNOPTICS_DELETE = prepend_synoptics('DELETE')
    SYNOPTICS_SCHEMA = prepend_synoptics('SCHEMA')