from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
from time import sleep
from server_common.utilities import print_and_log
HOST, PORT = '', 8008

_config = ""


class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """
        This is called by BaseHTTPRequestHandler every time a client does a GET.
        The response is written to self.wfile
        """
        if self.path == '/favicon.ico':
            pass
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        global _config
        self.wfile.write(_config)

    def log_message(self, format, *args):
        """ By overriding this method and doing nothing we disable writing to console
         for every client request. Remove this to re-enable """
        return


class Server(Thread):

    def run(self):
        server = HTTPServer(('', PORT), MyHandler)
        print_and_log("Serving HTTP on port %s ..." % PORT)
        server.serve_forever()

    def set_config(self, set_to):
        global _config
        _config = set_to


if __name__ == '__main__':
    server = Server()
    server.start()
    server.set_config("TEST")
    sleep(10)
    server.set_config("NOT TEST")