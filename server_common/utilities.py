import zlib
import datetime
import socket
import re
import json
from xml.etree import ElementTree

IOCLOG_HOST = "127.0.0.1"
IOCLOG_PORT = 7004


def compress_and_hex(value):
    """Compresses the inputted string and encodes it as hex.

    Args:
        value (string) : The string to be compressed
    Returns:
        string : A compressed and hexed version of the inputted string
    """
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value (string) : The string to be decompressed, encoded in hex

    Returns:
        string : A decompressed version of the inputted string
    """
    return zlib.decompress(value.decode("hex"))


def convert_to_json(value):
    """Converts the inputted object to JSON format.

    Args:
        value (obj) : The object to be converted

    Returns:
        string : The JSON representation of the inputted object
    """
    return json.dumps(value).encode('ascii', 'replace')


def convert_from_json(value):
    """Converts the inputted string into a JSON object.

    Args:
        value (string) : The JSON representation of an object

    Returns:
        obj : An object corresponding to the given string
    """
    return json.loads(value)


def parse_boolean(string):
    """Parses an xml true/false value to boolean

    Args:
        string (string) : String containing the xml representation of true/false

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


def write_to_ioc_log(message, severity="INFO", src="BLOCKSVR"):
    """Writes a message to the IOC log. It is preferable to use print_and_log for easier debugging.

    Args:
        severity (string, optional) : Gives the severity of the message. Expected serverities are MAJOR, MINOR and INFO.
                                    Default severity is INFO
        src (string, optional) : Gives the source of the message. Default source is BLOCKSVR
    """
    if severity not in ['INFO','MINOR','MAJOR','FATAL'] :
        print "write_to_ioc_log: invalid severity ", severity
        return
    msg_time = datetime.datetime.utcnow()
    msg_time_str = msg_time.isoformat()
    if msg_time.utcoffset() is None:
        msg_time_str += "Z"

    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    xml += "<message>"
    xml += "<clientName>%s</clientName>" % src
    xml += "<severity>%s</severity>" % severity
    xml += "<contents><![CDATA[%s]]></contents>" % message
    xml += "<type>ioclog</type>"
    xml += "<eventTime>%s</eventTime>" % msg_time_str
    xml += "</message>\n"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((IOCLOG_HOST, IOCLOG_PORT))
        sock.sendall(xml)
    except Exception as err:
        print "Could not send message to IOC log: %s" % err
    finally:
        if sock is not None:
            sock.close()


def value_list_to_xml(list, grp, group_tag, item_tag):
    """Converts a list of values to corresponding xml.

    Args:
        list (list) : The list of values given in the format of [name, {parameter : value, parameter : value}]
        grp (ElementTree.SubElement) : The SubElement object to append the list on to
        group_tag (string) : The tag that corresponds to the group for the items given in the list e.g. macros
        item_tag (string) : The tag that corresponds to each item in the list e.g. macro
    """
    xml_list = ElementTree.SubElement(grp, group_tag)
    if len(list) > 0:
        for n, c in list.iteritems():
            xml_item = ElementTree.SubElement(xml_list, item_tag)
            xml_item.set("name", n)
            for cn, cv in c.iteritems():
                xml_item.set(str(cn), str(cv).lower())


def check_pv_name_valid(name):
    """Checks that text conforms to the ISIS PV naming standard

    Args:
        name (string) : The text to be checked

    Returns:
        bool : True if text conforms to standard, False otherwise
    """
    if re.match(r"[A-Za-z0-9_]*", name) is None:
        return False
    return True


def create_pv_name(name, current_pvs, default_pv):
    """Uses the given name as a basis for a valid PV.

    Args:
        name (string) : The basis for the PV
        current_pvs (list) : List of already allocated pvs
        default_pv (string) : Basis for the PV if name is unreasonable

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
        file_path (string) : The location of the xml file

    Returns:
        Element : A object holding all the xml information
    """
    it = ElementTree.iterparse(file_path)
    for _, el in it:
        if ':' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return it.root


def print_and_log(message, severity="INFO", src="BLOCKSVR"):
    """Prints the specified message to the console and writes it to the IOC log.

    Args:
        severity (string, optional) : Gives the severity of the message. Expected serverities are MAJOR, MINOR and INFO.
                                    Default severity is INFO.
        src (string, optional) : Gives the source of the message. Default source is BLOCKSVR.
    """
    print "%s: %s" % (severity, message)
    write_to_ioc_log(message, severity, src)

