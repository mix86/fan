# encoding: utf-8
import sys
import re
import urllib, urllib2
import getopt
from time import sleep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header

counter = None

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global counter
        cl, cl2 = parse_header(self.headers.get('content-length'))
        qs = self.rfile.read(int(cl))
        post_data = qs.decode()

        self.wfile.write("HTTP/1.1 200 OK\n");
        self.wfile.write("Content-Type: text/html\n")
        self.wfile.write("\n")
        self.wfile.write("OK\n")

        numbers = re.findall("Some text: (\d+)", post_data)

        for n in numbers:
            n = int(n)
            if counter:
                assert (n == counter + 1 or n == 0)
            counter = n
            # sys.stdout.write('%d ' % n)
            # sys.stdout.flush()

        sys.stdout.write('.')
        sys.stdout.flush()



def subscribe(hub, host, port, topic, unsub=False):
    url = '%s/sub/' % hub
    data = urllib.urlencode({
        'hub.callback': 'http://%s:%d/' % (host, port),
        'hub.topic': topic,
        'hub.mode': unsub and 'unsubscribe' or 'subscribe',
    })
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    response.read()


def parse_args():
    host = '127.0.0.1'
    port = 8001
    hub = 'http://127.0.0.1:8080'
    topic = 'foo'
    verbose = False
    argv = sys.argv
    try:
        opts, args = getopt.getopt(
                argv[1:],
                "hv",
                ["host=", "port=", "hub=", "topic=", "help", "verbose"]
            )
    except getopt.error:
        raise

    verbose, dry = False, False
    for option, value in opts:
        if option in ("-v", "--verbose"):
            verbose = True
        elif option in ("-h", "--help"):
            raise Exception
        elif option == "--host":
            host = value
        elif option == "--port":
            port = int(value)
        elif option == "--hub":
            hub = value
        elif option == "--topic":
            topic = value

    return host, port, hub, topic, verbose


def main(host, port, hub, topic, verbose=False):
    try:
        server = HTTPServer(('0.0.0.0', port), RequestHandler)
        subscribe(hub=hub, host=host, port=port, topic=topic)
        server.serve_forever()
    except (KeyboardInterrupt, AssertionError):
        subscribe(hub=hub, host=host, port=port, topic=topic, unsub=True)
        sleep(1)
        server.socket.close();
        print('bye!')


if __name__ == '__main__':
    main(*parse_args())
