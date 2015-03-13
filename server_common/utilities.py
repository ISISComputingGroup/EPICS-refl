import zlib
import datetime
import socket
import re
import json
from xml.etree import ElementTree

IOCLOG_HOST = "127.0.0.1"
IOCLOG_PORT = 7004


def compress_and_hex(value):
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    return zlib.decompress(value.decode("hex"))


def convert_to_json(value):
    return json.dumps(value).encode('ascii', 'replace')


def convert_from_json(value):
    return json.loads(value)


def parse_boolean(string):
    if string.lower() == "true":
        return True
    elif string.lower() == "false":
        return False
    else:
        raise ValueError(str(string) + ': Attribute must be "true" or "false"')


def write_to_ioc_log(message, severity="INFO", src="BLOCKSVR"):
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
    # Helper function to convert a list of values to XML
    xml_list = ElementTree.SubElement(grp, group_tag)
    if len(list) > 0:
        for n, c in list.iteritems():
            xml_item = ElementTree.SubElement(xml_list, item_tag)
            xml_item.set("name", n)
            for cn, cv in c.iteritems():
                xml_item.set(str(cn), str(cv).lower())


def check_pv_name_valid(name):
    if re.match(r"[A-Za-z0-9_]*", name) is None:
        return False
    return True


def parse_xml_removing_namespace(file_path):
    it = ElementTree.iterparse(file_path)
    for _, el in it:
        if ':' in el.tag:
            el.tag = el.tag.split('}',1)[1]
    return it.root


def print_and_log(message, severity="INFO", src="BLOCKSVR"):
    print "%s: %s" % (severity, message)
    write_to_ioc_log(message, severity, src)


def print_and_log(message, severity="INFO", src="BLOCKSVR"):
    print "%s: %s" % (severity, message)
    write_to_ioc_log(message, severity, src)

