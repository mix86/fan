# encoding: utf-8
import sys
import simplejson as json
from uuid import uuid4
from datetime import datetime

from twisted.web import server
from twisted.web.resource import Resource
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from fan.utils import StringProducer

from twisted.internet import reactor
from twisted.python import log

from fan.core.rss import RSS

log.startLogging(sys.stdout)

DOMAIN = 'http://127.0.0.1:8081'
HUB_URL = 'http://127.0.0.1:8080/pub/'

stack = []
entries = []

class Root(Resource):
    isLeaf = False

class Publisher(Resource):
    isLeaf = True
    def render_GET(self, request):
        global entries
        # urn = uuid4().get_urn()
        # updated = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        # topic = (
        #     '<?xml version="1.0" encoding="utf-8"?>\n'
        #     '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        #     '    <title>Example Feed</title>\n'
        #     '    <subtitle>A subtitle.</subtitle>\n'
        #     '    <link href="%(domain)s/feed/" rel="self" />\n'
        #     '    <id>%(urn)s</id>\n'
        #     '    <updated>%(updated)s</updated>\n'
        #     '%(entries)s'
        #     '</feed>\n'
        # ) % {
        #     'domain': DOMAIN,
        #     'urn': urn,
        #     'updated': updated,
        #     'entries': '\n'.join(entries),
        # }
        if entries:
            topic = RSS().generate(entries)
            entries = []
        else:
            topic = ''
        return topic

class Receiver(Resource):
    isLeaf = True
    def render_POST(self, request):
        topic = RSS().parse(request.content.read())
        for entry in topic.entries:
            sent_urn = entry['id']
            received_urn = stack[0]
            print '<=', sent_urn
            if sent_urn == received_urn:
                stack.pop(0)
                print 'OK'
            else:
                print 'FAIL'

        return 'OK'


def send_ping(ing):
    global entries, stack
    urn = uuid4().get_urn()
    updated = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    entry = {
        'topic': 'foo',
        'url': "%s/%s/" % (DOMAIN, urn),
        'data': {
            'title': 'foo',
            'link': "%s/%s/" % (DOMAIN, urn),
            'summary': 'Some text: %s.' % urn,
            'id': urn,
            'updated': updated,
        }
    }

    entries.append(entry)
    stack.append(urn)
    print '=>', urn

    body = StringProducer("hub.topic=foo&hub.url=%s/feed/" % DOMAIN)
    headers = Headers({
        'Content-Type': ['application/x-www-form-urlencoded'],
    })

    d = agent.request('POST', HUB_URL, headers, body)

    d.addCallback(ping_sent)
    d.addErrback(ping_not_sent)

ping_counter = 0

def ping_sent(response):
    global ping_counter
    print 'ping sent: ', response.code
    delay = 5 if ping_counter % 3 == 0 else 1
    # delay = 5
    ping_counter += 1
    reactor.callLater(delay, send_ping, None)

def ping_not_sent(error):
    print 'ping not send: ', error
    reactor.callLater(10, send_ping, None)

root = Root()
root.putChild("feed", Publisher())
root.putChild("receiver", Receiver())

agent = Agent(reactor)

reactor.listenTCP(8081, server.Site(root))

reactor.callLater(2, send_ping, None)


reactor.run()
