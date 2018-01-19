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

"""
Module with useful utilities in
"""
from datetime import datetime


def add_default_field(pv_name, default_field):
    """
    Add a default field to a pv name if pv_name does not already have a field and the default field makes sense.

     This is useful for example to add a VAL field to pvs for the archive

    Args:
        pv_name: the pv name
        default_field: default field to add

    Returns: pvname with the default field added

    """
    if default_field is None or default_field == "":
        return pv_name
    if pv_name is None or pv_name == "" or "." in pv_name:
        return pv_name
    return "{0}.{1}".format(pv_name, default_field)


def truncate(x, d):
    """
    Truncate a number to d decimal places
    Args:
        x: the number to truncate
        d: the number of decimal places; -ve to truncate to powers

    Returns: truncated number

    """
    if d > 0:
        mult = 10.0 ** d
        return int(x * mult) / mult
    else:
        mult = 10 ** (-d)
        return int(x / mult) * mult


def utc_time_now():
    """
    Returns: the current time in utc
    """
    return datetime.utcnow()
