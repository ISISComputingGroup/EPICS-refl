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

import os

BLOCKSERVER = "BLOCKSERVER:"


class BlockserverPVNames:
    """Holds and manages blockserver PV names
    """

    @staticmethod
    def prepend_blockserver(base_name):
        return BLOCKSERVER + base_name

    BLOCKNAMES = prepend_blockserver.__func__('BLOCKNAMES')
    BLOCK_DETAILS = prepend_blockserver.__func__('BLOCK_DETAILS')
    BLOCK_RULES = prepend_blockserver.__func__('BLOCK_RULES')
    GROUPS = prepend_blockserver.__func__('GROUPS')
    GROUP_RULES = prepend_blockserver.__func__('GROUP_RULES')
    COMPS = prepend_blockserver.__func__('COMPS')
    LOAD_CONFIG = prepend_blockserver.__func__('LOAD_CONFIG')
    SAVE_CONFIG = prepend_blockserver.__func__('SAVE_CONFIG')
    CLEAR_CONFIG = prepend_blockserver.__func__('CLEAR_CONFIG')
    CONF_DESC_RULES = prepend_blockserver.__func__('CONF_DESC_RULES')
    START_IOCS = prepend_blockserver.__func__('START_IOCS')
    STOP_IOCS = prepend_blockserver.__func__('STOP_IOCS')
    RESTART_IOCS = prepend_blockserver.__func__('RESTART_IOCS')
    CONFIGS = prepend_blockserver.__func__('CONFIGS')
    GET_CURR_CONFIG_DETAILS = prepend_blockserver.__func__('GET_CURR_CONFIG_DETAILS')
    SET_CURR_CONFIG_DETAILS = prepend_blockserver.__func__('SET_CURR_CONFIG_DETAILS')
    SAVE_NEW_CONFIG = prepend_blockserver.__func__('SAVE_NEW_CONFIG')
    SAVE_NEW_COMPONENT = prepend_blockserver.__func__('SAVE_NEW_COMPONENT')
    SERVER_STATUS = prepend_blockserver.__func__('SERVER_STATUS')
    DELETE_CONFIGS = prepend_blockserver.__func__('DELETE_CONFIGS')
    DELETE_COMPONENTS = prepend_blockserver.__func__('DELETE_COMPONENTS')
    BLANK_CONFIG = prepend_blockserver.__func__('BLANK_CONFIG')
    BUMPSTRIP_AVAILABLE = prepend_blockserver.__func__('BUMPSTRIP_AVAILABLE')
    BUMPSTRIP_AVAILABLE_SP = prepend_blockserver.__func__('BUMPSTRIP_AVAILABLE:SP')
    GET_SCREENS = prepend_blockserver.__func__('GET_SCREENS')
    SET_SCREENS = prepend_blockserver.__func__('SET_SCREENS')
    SCREENS_SCHEMA = prepend_blockserver.__func__('SCREENS_SCHEMA')

    @staticmethod
    def get_config_details_pv(pv_key):
        GET_CONFIG_DETAILS = ":GET_CONFIG_DETAILS"
        return BlockserverPVNames.prepend_blockserver(pv_key + GET_CONFIG_DETAILS)

    @staticmethod
    def get_component_details_pv(pv_key):
        GET_COMPONENT_DETAILS = ":GET_COMPONENT_DETAILS"
        return BlockserverPVNames.prepend_blockserver(pv_key + GET_COMPONENT_DETAILS)

    @staticmethod
    def get_dependencies_pv(pv_key):
        DEPENDENCIES = ":DEPENDENCIES"
        return BlockserverPVNames.prepend_blockserver(pv_key + DEPENDENCIES)
