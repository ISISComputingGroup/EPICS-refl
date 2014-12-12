import zlib
import datetime
import socket
from xml.etree import ElementTree

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


def write_to_ioc_log(message, severity, src):
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




