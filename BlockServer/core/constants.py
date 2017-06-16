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

"""Contains string constants used by the modules of the config package"""
import os

GRP_NONE = "NONE"

TAG_NAME = 'name'
TAG_VALUE = 'value'

TAG_BLOCKS = 'blocks'
TAG_GROUPS = 'groups'
TAG_IOCS = 'iocs'
TAG_COMPONENTS = 'components'
TAG_MACROS = 'macros'
TAG_PVS = 'pvs'
TAG_PVSETS = 'pvsets'
TAG_EDITS = 'edits'

TAG_BLOCK = 'block'
TAG_GROUP = 'group'
TAG_IOC = 'ioc'
TAG_COMPONENT = 'component'
TAG_MACRO = 'macro'
TAG_PV = 'pv'
TAG_PVSET = 'pvset'
TAG_EDIT = 'edit'

TAG_LOCAL = 'local'
TAG_READ_PV = 'read_pv'
TAG_VISIBLE = 'visible'
TAG_RUNCONTROL_ENABLED = 'rc_enabled'
TAG_RUNCONTROL_LOW = 'rc_lowlimit'
TAG_RUNCONTROL_HIGH = 'rc_highlimit'
TAG_LOG_PERIODIC = 'log_periodic'
TAG_LOG_RATE = 'log_rate'
TAG_LOG_DEADBAND = 'log_deadband'

TAG_AUTOSTART = 'autostart'
TAG_RESTART = 'restart'
TAG_SIMLEVEL = 'simlevel'

TAG_RC_LOW = ":RC:LOW"
TAG_RC_HIGH = ":RC:HIGH"
TAG_RC_ENABLE = ":RC:ENABLE"
TAG_RC_OUT_LIST = "CS:RC:OUT:LIST"

SIMLEVELS = ['recsim', 'devsim']

# Name of default component that is loaded with every configuration.
# Contains essential IOCs (and blocks/groups?) e.g. DAE, INSTETC
DEFAULT_COMPONENT = "_base"
EXAMPLE_DEFAULT = os.path.join("BlockServer", "example_base")  # Relative to MYDIRBLOCK

FILENAME_BLOCKS = "blocks.xml"
FILENAME_GROUPS = "groups.xml"
FILENAME_IOCS = "iocs.xml"
FILENAME_COMPONENTS = "components.xml"
FILENAME_META = "meta.xml"
FILENAME_SCREENS = "screens.xml"

SCHEMA_FOR = [FILENAME_BLOCKS, FILENAME_GROUPS, FILENAME_IOCS, FILENAME_COMPONENTS, FILENAME_META]
