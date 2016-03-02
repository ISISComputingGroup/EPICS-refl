import datetime
import socket


class IsisLogger(object):
    def __init__(self):
        super(IsisLogger, self).__init__()
        self.ioclog_host = "127.0.0.1"
        self.ioclog_port = 7004

    def write_to_log(self, message, severity="INFO", src="BLOCKSVR"):
        """Writes a message to the IOC log. It is preferable to use print_and_log for easier debugging.
        Args:
            severity (string, optional): Gives the severity of the message. Expected serverities are MAJOR, MINOR and INFO.
                                        Default severity is INFO
            src (string, optional): Gives the source of the message. Default source is BLOCKSVR
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
            sock.connect((self.ioclog_host, self.ioclog_port))
            sock.sendall(xml)
        except Exception as err:
            print "Could not send message to IOC log: %s" % err
        finally:
            if sock is not None:
                sock.close()