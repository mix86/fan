# encoding: utf-8
from datetime import datetime
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.internet.defer import Deferred

from twisted.web.server import NOT_DONE_YET
from base import BaseHandler
from utils import StringProducer

agent = Agent(reactor)

class Subscription(object):
    def __init__(self, db):
        super(Subscription, self).__init__()
        self.db = db
        self._db = db.sub

    def find(self, success, host=None, feed=None, failure=None):
        q = {}

        if host:
            q.update({"host": host})

        if feed:
            q.update({"feed": feed})

        d = self._db.find(q)
        d.addCallback(*success)

        if failure:
            d.addErrback(*failure)

    def create(self, host, feed):
        self.find(host=host, feed=feed, success=(self._really_create, host, feed))

    def _really_create(self, exist, host, feed):
        if exist:
            log.msg('Did nothing. Host %(host)s already subscribed on %(feed)s\n' % {
                'host': host,
                'feed': feed,
            })
            return

        self._db.insert({"feed": feed, 'host': host})

        log.msg('Host %(host)s subscribed on %(feed)s\n' % {
            'host': host,
            'feed': feed,
        })

    def remove(self, host, feed=None):

        if feed is not None:
            raise NotImplementedError

        self._db.remove({'host': host})

        log.msg('All subscribtions of host %(host)s removed\n' % {
            'host': host,
        })

    def send_news(self, feed):
        log.msg('Send news called for %s' % feed)
        self.find(feed=feed, success=(self._really_send_news, feed))

    def _really_send_news(self, sub_list, feed):
        log.msg('Sending news to %d subscribers' % len(sub_list))
        for sub in sub_list:
            host = sub['host']
            # since = sub['time']
            body = StringProducer("foo=bar")
            headers = Headers({
                'User-Agent': ['PubSubHub'],
                'Content-Type': ['application/x-www-form-urlencoded'],
            })
            d = agent.request('POST',
                              str("http://%s/" % host),
                              headers,
                              body)
            d.addCallback(self.mark_as_sent, feed=feed, host=host, time=datetime.now())

    def mark_as_sent(self, response, feed, host, time):
        if response.code != 200:
            raise NotImplementedError

        self._db.update({
            "feed": feed,
            'host': host,
        }, {
            '$set': {"last": time},
        })
        log.msg('Feed %(feed)s marked as sent for host %(host)s at %(time)s' % vars())



class NewsSender(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def dataReceived(self, bytes):
        pass

    def connectionLost(self, reason):
        self.finished.callback()


class SubscribeHandler(BaseHandler, Resource):

    def parse_request(self, request):
        try:
            feed = request.args["feed"][0] #TODO: не только один первый
        except (KeyError):
            feed = None
        try:
            host = request.args["host"][0]
        except (KeyError):
            host = request.client.host

        return {"feed": feed, "host": host}

    def render_GET(self, request):
        """Get subscriptions for host"""
        params = self.parse_request(request)
        Subscription(self.db).find(host=params['host'],
                                   feed=params['feed'],
                                   success=(self._success, request),
                                   failure=(self._failure, request),
                                )
        return NOT_DONE_YET

    def render_POST(self, request):
        params = self.parse_request(request)
        Subscription(self.db).create(params['host'], params['feed'])
        return self.mk_response(True, None)

    def render_DELETE(self, request):
        Subscription(self.db).remove(self.get_host(request))
        return self.mk_response(True, None)
