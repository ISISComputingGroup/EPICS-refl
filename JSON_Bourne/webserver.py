from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
from time import sleep
from get_webpage import scrape_webpage
import json
HOST, PORT = '', 60000


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
        self.wfile.write(json.dumps(scrape_webpage()))

    def log_message(self, format, *args):
        """ By overriding this method and doing nothing we disable writing to console
         for every client request. Remove this to re-enable """
        return


class Server(Thread):

    def run(self):
        server = HTTPServer(('', PORT), MyHandler)
        server.serve_forever()


if __name__ == '__main__':
    try:
        server = Server()
        server.start()
    except e as KeyboardInterrupt:
        server.join()