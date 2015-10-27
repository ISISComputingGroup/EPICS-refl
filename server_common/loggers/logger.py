class Logger(object):
    def __init__(self):
        pass

    def write_to_log(self, message, severity="INFO", src="BLOCKSVR"):
        """Writes a message to the log. Needs to be implemented in child class.
        Args:
            severity (string, optional) : Gives the severity of the message. Expected serverities are MAJOR, MINOR
                                          and INFO (default).
            src (string, optional) : Gives the source of the message. Default source is BLOCKSVR
        """
        pass
