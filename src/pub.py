# encoding: utf-8

import uuid
from datetime import datetime

from twisted.web.resource import Resource
from base import BaseHandler
from twisted.python import log

from twisted.internet import reactor
from twisted.internet.protocol import Protocol

from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.internet.defer import Deferred

from sub import Subscription


agent = Agent(reactor)

class FeedGrabber(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.response = ''

    def parse_response(self, data):
        #TODO убрать заглушки
        return datetime.now(), uuid.uuid4().hex, data

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.parse_response(self.response))


class Feed(object):
    def __init__(self, db, name, url):
        super(Feed, self).__init__()
        self.db = db
        self._db = db.feed
        self.name = name
        self.url = url

    def create_feed_update(self, params):

        time, update_id, data = params

        self._db.insert({
            "feed": self.name,
            'url': self.url,
            'data': data,
            'time': time,
        }, safe=True)

        log.msg('New item %(update_id)s in feed %(feed)s\n' % {
            'update_id': update_id,
            'feed': self.name,
        })

        Subscription(self.db).send_news(feed=self.name)

    def process_news(self, response):
        finished = Deferred()
        finished.addCallback(self.create_feed_update)
        response.deliverBody(FeedGrabber(finished))
        return finished

    def get_news(self):
        headers = Headers({'User-Agent': ['PubSubHub']})
        d = agent.request('GET', self.url, headers, None)
        d.addCallback(self.process_news)


class PublishHandler(BaseHandler, Resource):
    def parse_request(self, request):
        try:
            feed = request.args["feed"][0] #TODO: не только один первый
        except (KeyError):
            feed = None
        try:
            url = request.args["url"][0]
        except (KeyError):
            url = request.client.host

        return {"feed": feed, "url": url}


    def render_POST(self, request):
        params = self.parse_request(request)
        url, feed = params['url'], params['feed']
        Feed(self.db, name=feed, url=url).get_news()
        return self.mk_response(True, None)
