import zlib
import datetime
import socket
import re
from xml.etree import ElementTree
from config.constants import TAG_NAME

IOCLOG_HOST = "127.0.0.1"
IOCLOG_PORT = 7004


def compress_and_hex(value):
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    return zlib.decompress(value.decode("hex"))


def parse_boolean(string):
    if string.lower() == "true":
        return True
    elif string.lower() == "false":
        return False
    else:
        raise ValueError(str(string) + ': Attribute must be "true" or "false"')


def write_to_ioc_log(message, severity="INFO", src="BLOCKSVR"):
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


def print_and_log(message, severity="INFO", src="BLOCKSVR"):
    print "%s: %s" % (severity, message)
    write_to_ioc_log(message, severity, src)

def value_list_to_xml(list, grp, group_tag, item_tag):
    #Helper function to convert a list of values to XML
    if len(list) > 0:
        xml_list = ElementTree.SubElement(grp, group_tag)
        for n, c in list.iteritems():
            xml_item = ElementTree.SubElement(xml_list, item_tag)
            xml_item.set(TAG_NAME, n)
            for cn, cv in c.iteritems():
                xml_item.set(str(cn), str(cv))


def check_config_name_valid(name):
    if re.match(r"[A-Za-z0-9_]*", name) is None:
        raise Exception("Config contains invalid characters: " + name)


if __name__ == '__main__':
    write_to_ioc_log("Hello")



