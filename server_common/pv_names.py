# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
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

BLOCKSERVER = "BLOCKSERVER:"


def prepend_blockserver(base_name):
    return BLOCKSERVER + base_name


class DatabasePVNames:
    """
    Holds and manages database server PV names.
    """
    IOCS = prepend_blockserver('IOCS')
    HIGH_INTEREST = prepend_blockserver('PVS:INTEREST:HIGH')
    MEDIUM_INTEREST = prepend_blockserver('PVS:INTEREST:MEDIUM')
    FACILITY = prepend_blockserver('PVS:INTEREST:FACILITY')
    ACTIVE_PVS = prepend_blockserver('PVS:ACTIVE')
    ALL_PVS = prepend_blockserver('PVS:ALL')
    SAMPLE_PARS = prepend_blockserver('SAMPLE_PARS')
    BEAMLINE_PARS = prepend_blockserver('BEAMLINE_PARS')
    USER_PARS = prepend_blockserver('USER_PARS')
    IOCS_NOT_TO_STOP = prepend_blockserver('IOCS_NOT_TO_STOP')


class BlockserverPVNames:
    """Holds and manages blockserver PV names
    """
    BLOCKNAMES = prepend_blockserver('BLOCKNAMES')
    BLOCK_DETAILS = prepend_blockserver('BLOCK_DETAILS')
    BLOCK_RULES = prepend_blockserver('BLOCK_RULES')
    GROUPS = prepend_blockserver('GROUPS')
    GROUP_RULES = prepend_blockserver('GROUP_RULES')
    COMPS = prepend_blockserver('COMPS')
    LOAD_CONFIG = prepend_blockserver('LOAD_CONFIG')
    SAVE_CONFIG = prepend_blockserver('SAVE_CONFIG')
    CLEAR_CONFIG = prepend_blockserver('CLEAR_CONFIG')
    RELOAD_CURRENT_CONFIG = prepend_blockserver('RELOAD_CURRENT_CONFIG')
    CONF_DESC_RULES = prepend_blockserver('CONF_DESC_RULES')
    START_IOCS = prepend_blockserver('START_IOCS')
    STOP_IOCS = prepend_blockserver('STOP_IOCS')
    RESTART_IOCS = prepend_blockserver('RESTART_IOCS')
    CONFIGS = prepend_blockserver('CONFIGS')
    GET_CURR_CONFIG_DETAILS = prepend_blockserver('GET_CURR_CONFIG_DETAILS')
    SET_CURR_CONFIG_DETAILS = prepend_blockserver('SET_CURR_CONFIG_DETAILS')
    SAVE_NEW_CONFIG = prepend_blockserver('SAVE_NEW_CONFIG')
    SAVE_NEW_COMPONENT = prepend_blockserver('SAVE_NEW_COMPONENT')
    SERVER_STATUS = prepend_blockserver('SERVER_STATUS')
    DELETE_CONFIGS = prepend_blockserver('DELETE_CONFIGS')
    DELETE_COMPONENTS = prepend_blockserver('DELETE_COMPONENTS')
    BLANK_CONFIG = prepend_blockserver('BLANK_CONFIG')
    ALL_COMPONENT_DETAILS = prepend_blockserver('ALL_COMPONENT_DETAILS')
    GET_SCREENS = prepend_blockserver('GET_SCREENS')
    SET_SCREENS = prepend_blockserver('SET_SCREENS')
    BANNER_DESCRIPTION = prepend_blockserver('BANNER_DESCRIPTION')
    SCREENS_SCHEMA = prepend_blockserver('SCREENS_SCHEMA')
    
    @staticmethod
    def get_config_details_pv(pv_key):
        return prepend_blockserver(pv_key + ":GET_CONFIG_DETAILS")

    @staticmethod
    def get_component_details_pv(pv_key):
        return prepend_blockserver(pv_key + ":GET_COMPONENT_DETAILS")

    @staticmethod
    def get_dependencies_pv(pv_key):
        return prepend_blockserver(pv_key + ":DEPENDENCIES")
