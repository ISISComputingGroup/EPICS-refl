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

"""
Set of shared utilities and constants for rules
"""

"""Standard Regex in Java for PV like names,
e.g. name must start with a letter and only contain letters, numbers and underscores"""
REGEX_PV_NAME_LIKE = r"^[a-zA-Z]\w*$"

"""Standard Error message template for when regex for PV like names failes.
Usage REGEX_ERROR_TEMPLATE_PV_NAME.format(<object name>)"""
REGEX_ERROR_TEMPLATE_PV_NAME = "{0} name must start with a letter and only contain letters, numbers and underscores"
