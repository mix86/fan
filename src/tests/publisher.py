# encoding: utf-8
import sys
sys.path = [
    '/home/mixael/dev/pubsub_proto/src',
] + sys.path
import getopt
import threading
import urllib, urllib2
from time import sleep
from datetime import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from fan.core.rss import RSS

_running = True
entries_generator = None

def _entries_generator(host, port, topic):
    counter = 0
    while True:
        updated = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        content = str(counter)
        # sys.stdout.write('%s ' % content)
        # sys.stdout.flush()
        yield {
            'topic': topic,
            'url': "http://%s:%d/%s/" % (host, port, content),
            'data': {
                'title': 'foo',
                'link': "http://%s:%d/%s/" % (host, port, content),
                'summary': 'Some text: %s.' % content,
                'id': content,
                'updated': updated,
            }
        }
        counter += 1


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.wfile.write("HTTP/1.1 200 OK\n");
        self.wfile.write("Content-Type: text/html\n")
        self.wfile.write("\n")
        entries = [entries_generator.next() for i in range(int(1))]
        self.wfile.write(RSS().generate(entries)+"\n")


class Pinger(threading.Thread):
    def __init__(self, host, port, hub, topic, interval, verbose, *args, **kw):
        super(Pinger, self).__init__(*args, **kw)
        self.host = host
        self.port = port
        self.hub = hub
        self.topic = topic
        self.interval = interval
        self.verbose = verbose

    def run(self):
        global _running
        while _running:
            sys.stdout.write('.')
            sys.stdout.flush()
            url = '%s/pub/' % self.hub
            data = urllib.urlencode({
                'hub.topic': self.topic,
                'hub.url': 'http://%s:%s/' % (self.host, self.port)
            })
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            req = urllib2.Request(url, data, headers)
            response = urllib2.urlopen(req)
            response.read()
            sleep(self.interval)


def parse_args():
    host = '127.0.0.1'
    port = 8000
    hub = 'http://127.0.0.1:8080'
    topic = 'foo'
    interval = 1
    verbose = False
    argv = sys.argv
    try:
        opts, args = getopt.getopt(
                argv[1:],
                "hv",
                ["host=", "port=", "hub=", "topic=", "interval=", "help", "verbose"]
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
        elif option == "--interval":
            interval = float(value)

    return host, port, hub, topic, interval, verbose


def main(host, port, hub, topic, interval, verbose=False):
    global _running, entries_generator
    try:
        entries_generator = _entries_generator(host=host, port=port, topic=topic)
        server = HTTPServer(('0.0.0.0', port), RequestHandler)
        pinger = Pinger(host, port, hub, topic, interval, verbose)
        pinger.start()
        server.serve_forever()

    except KeyboardInterrupt:
        _running = False
        pinger.join()
        sleep(5)
        server.socket.close();
        print('bye!')

if __name__ == '__main__':
    main(*parse_args())
