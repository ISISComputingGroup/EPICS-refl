import urllib2


class ArchiverWrapper(object):
    def restart_archiver(self):
        # Set to ignore proxy for localhost
        proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)
        urllib2.install_opener(opener)
        urllib2.urlopen("http://localhost:4813/restart")
