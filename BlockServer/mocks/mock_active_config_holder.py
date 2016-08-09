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
import copy
from BlockServer.config.configuration import Configuration


class MockActiveConfigHolder(object):
    def __init__(self, macros):
        self.config_name = ""
        self.config = Configuration(macros)
        self.blocks = dict()

    def get_config_name(self):
        return self.config_name

    def set_config_name(self, name):
        # This does not exist in the real thing
        self.config_name = name

    def get_block_details(self):
        blks = copy.deepcopy(self.config.blocks)
        # for cn, cv in self.components.iteritems():
        #     for bn, bv in cv.blocks.iteritems():
        #         if bn not in blks:
        #             blks[bn] = bv
        return blks

    def add_block(self, blockargs):
        self.config.add_block(**blockargs)


