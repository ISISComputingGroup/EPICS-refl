from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
HOST, PORT = '', 8008
from time import sleep

# This is a global variable as it's easier with threading and the way the handler class is defined
# TODO: Fix later!!
_response = ""

class myHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        global _response
        self.wfile.write(_response)

class Server(Thread):

    def run(self):
        self.server = HTTPServer(('',PORT), myHandler)
        print "Serving HTTP on port %s ..." % PORT
        self.server.serve_forever()

    def set_text(self,set_text_to):
        global _response
        _response = set_text_to


if __name__ == '__main__':
    server = Server()
    server.start()
    server.set_text("TEST")
    sleep(10)
    server.set_text("NOT TEST")