# encoding: utf-8

import feedparser
from datetime import datetime

from twisted.web.resource import Resource
from base import BaseHandler
from twisted.python import log

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.error import AlreadyCalled

from twisted.web.client import Agent
from twisted.internet.defer import Deferred

from sub import Subscription
from base import Controller, ParametrizedSingleton

agent = Agent(reactor)


class FeedFetcher(Protocol):
    def __init__(self, edges, finished):
        self.finished = finished
        self.response = ''
        self.left_edge = edges[0]
        self.right_edge = edges[1]

    def parse_response(self, data):
        feed = feedparser.parse(data)
        for entry in feed.entries:
            updated_parsed = entry.pop('updated_parsed')
            updated = datetime(*(updated_parsed[:6] + updated_parsed[7:8]))
            if self.left_edge <= updated <= self.right_edge or 1:
                yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.parse_response(self.response))


class Feed(Controller):
    collection = 'feed'

    def create_feed_entry(self, generator, feed, url):
        i = 0
        for entry, updated in generator:
            self.db.feed.insert({
                'feed': feed,
                'url': url,
                'data': entry,
                'time': updated,
            }, safe=True)
            i += 1

        log.msg('Fetched %(i)d entries in feed %(feed)s' % vars())

        # self.db.ping.remove({
        #     'feed': feed,
        #     'url': url,
        #     'locked': self.id(),
        # })

        # Subscription(self.db).send_news(feed=feed)

    def process_news(self, response, feed, url, edges):

        finished = Deferred()

        finished.addCallback(self.create_feed_entry, feed=feed, url=url)

        response.deliverBody(FeedFetcher(edges=edges, finished=finished))

        return finished


    def get_news(self, cb_result, feed, url):

        self.db.ping.update({
            'feed': feed,
            'url': url,
            'locked': False,
        }, {
            '$set': {'locked': self.id()},
        }, multi=True, safe=True)

        d = self.db.ping.find({
            'feed': feed,
            'url': url,
            'locked': self.id(),
        })

        d.addCallback(self.get_news_slice, feed, url)

    def get_news_slice(self, result, feed, url):
        edges = result[0]['time'], result[-1]['time']
        d = agent.request('GET', url)
        d.addCallback(self.process_news, feed=feed, url=url, edges=edges)

    def register_ping(self, feed, url, time):
        self.db.ping.insert({
            'feed': feed,
            'url': url,
            'time': time,
            'locked': False,
        }, safe=True)

        d = Deferred()
        d.addCallback(self.get_news, feed=feed, url=url)

        FeedEntryBuffer(feed).put(d)


class FeedEntryBuffer(ParametrizedSingleton):
    delay = 1

    def put(self, d):
        try:
            self.delayed.cancel()
        except (AttributeError, AlreadyCalled):
            pass

        self.delayed = reactor.callLater(self.delay, d.callback, None)


class PublishHandler(BaseHandler, Resource):
    def render_POST(self, request):
        try:
            feed = request.args["feed"][0].strip()
            url = request.args["url"][0].strip()
        except (KeyError):
            return self.mk_response(None, True)

        time = datetime.now()

        Feed(self.db).register_ping(feed=feed, url=url, time=time)

        return self.mk_response(True, None)
