from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
HOST, PORT = '', 8008

class myHandler(BaseHTTPRequestHandler):
    text = ""

    def set_text(self):
        global text
        text = server.set_text

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(self.text)

class Server(Thread):
    def run(self):
        server=HTTPServer(('',PORT), myHandler)
        print "Serving HTTP on port %s ..." % PORT
        server.serve_forever()

    def set_text(self):
        global text
        text = server.set_text

if __name__ == '__main__':
    server = Server()
    server.start()