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

import zlib
import re
import json
from xml.etree import ElementTree

from loggers.logger import Logger


# Default to base class - does not actually log anything
LOGGER = Logger()


def set_logger(logger):
    """Sets the logger used by the print_and_log function.

    Args:
        logger (Logger): The logger to use. Must inherit from Logger.
    """
    global LOGGER
    LOGGER = logger


def print_and_log(message, severity="INFO", src="BLOCKSVR"):
    """Prints the specified message to the console and writes it to the log.

    Args:
        severity (string, optional): Gives the severity of the message. Expected serverities are MAJOR, MINOR and INFO.
                                    Default severity is INFO.
        src (string, optional): Gives the source of the message. Default source is BLOCKSVR.
    """
    print "%s: %s" % (severity, message)
    LOGGER.write_to_log(message, severity, src)


def compress_and_hex(value):
    """Compresses the inputted string and encodes it as hex.

    Args:
        value (string): The string to be compressed
    Returns:
        string : A compressed and hexed version of the inputted string
    """
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value (string): The string to be decompressed, encoded in hex

    Returns:
        string : A decompressed version of the inputted string
    """
    return zlib.decompress(value.decode("hex"))


def convert_to_json(value):
    """Converts the inputted object to JSON format.

    Args:
        value (obj): The object to be converted

    Returns:
        string : The JSON representation of the inputted object
    """
    return json.dumps(value).encode('ascii', 'replace')


def convert_from_json(value):
    """Converts the inputted string into a JSON object.

    Args:
        value (string): The JSON representation of an object

    Returns:
        obj : An object corresponding to the given string
    """
    return json.loads(value)


def parse_boolean(string):
    """Parses an xml true/false value to boolean

    Args:
        string (string): String containing the xml representation of true/false

    Returns:
        bool : A python boolean representation of the string

    Raises:
        ValueError : If the supplied string is not "true" or "false"
    """
    if string.lower() == "true":
        return True
    elif string.lower() == "false":
        return False
    else:
        raise ValueError(str(string) + ': Attribute must be "true" or "false"')


def value_list_to_xml(list, grp, group_tag, item_tag):
    """Converts a list of values to corresponding xml.

    Args:
        list (list): The list of values given in the format of [name, {parameter : value, parameter : value}]
        grp (ElementTree.SubElement): The SubElement object to append the list on to
        group_tag (string): The tag that corresponds to the group for the items given in the list e.g. macros
        item_tag (string): The tag that corresponds to each item in the list e.g. macro
    """
    xml_list = ElementTree.SubElement(grp, group_tag)
    if len(list) > 0:
        for n, c in list.iteritems():
            xml_item = ElementTree.SubElement(xml_list, item_tag)
            xml_item.set("name", n)
            for cn, cv in c.iteritems():
                xml_item.set(str(cn), str(cv))


def check_pv_name_valid(name):
    """Checks that text conforms to the ISIS PV naming standard

    Args:
        name (string): The text to be checked

    Returns:
        bool : True if text conforms to standard, False otherwise
    """
    if re.match(r"[A-Za-z0-9_]*", name) is None:
        return False
    return True


def create_pv_name(name, current_pvs, default_pv):
    """Uses the given name as a basis for a valid PV.

    Args:
        name (string): The basis for the PV
        current_pvs (list): List of already allocated pvs
        default_pv (string): Basis for the PV if name is unreasonable

    Returns:
        string : A valid PV
    """
    pv_text = name.upper().replace(" ", "_")
    pv_text = re.sub(r'\W', '', pv_text)
    # Check some edge cases of unreasonable names
    if re.search(r"[^0-9_]", pv_text) is None or pv_text == '':
        pv_text = default_pv

    # Make sure PVs are unique
    i = 0
    pv = pv_text

    while pv in current_pvs:
        pv = pv_text + str(i)
        i += 1

    return pv


def parse_xml_removing_namespace(file_path):
    """Creates an Element object from a given xml file, removing the namespace.

    Args:
        file_path (string): The location of the xml file

    Returns:
        Element : A object holding all the xml information
    """
    it = ElementTree.iterparse(file_path)
    for _, el in it:
        if ':' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return it.root


def waveform_to_string(data):
    output = ""
    for i in data:
        if i == 0:
            break
        output += str(unichr(i))
    return output

