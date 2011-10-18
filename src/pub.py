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


class TopicFetcher(Protocol):
    def __init__(self, edges, finished):
        self.finished = finished
        self.response = ''
        self.left_edge = edges[0]
        self.right_edge = edges[1]

    def parse_response(self, data):
        topic = feedparser.parse(data)
        for entry in topic.entries:
            entry.pop('updated_parsed')
            #TODO: feedprser date parse
            updated = datetime.strptime(entry['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if self.left_edge <= updated <= self.right_edge or 1:
                yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.parse_response(self.response))


class Topic(Controller):
    collection = 'topic'

    def create_feed_entries(self, generator, topic, url):
        i = 0
        for entry, updated in generator:
            print 'updated', updated, type(updated)
            print 'got', entry['id']
            self.db.topic.insert({
                'topic': topic,
                'url': url,
                'data': entry,
                'time': updated,
            }, safe=True)
            i += 1

        log.msg('Fetched %(i)d entries in topic %(topic)s' % vars())

        Subscription(self.db).send_news(topic=topic)

    def get_feed_entries(self, topic, since):
        d = self.db.topic.find({
            'topic': topic,
            'time': {'$gt': since},
        })

        return d

    def process_news(self, response, topic, url, edges):
        finished = Deferred()
        finished.addCallback(self.create_feed_entries, topic=topic, url=url)
        response.deliverBody(TopicFetcher(edges=edges, finished=finished))
        return finished


    def get_news(self, cb_result, topic, url):

        self.db.ping.update({
            'topic': topic,
            'url': url,
            'locked': False,
        }, {
            '$set': {'locked': self.id()},
        }, multi=True, safe=True)

        d = self.db.ping.find({
            'topic': topic,
            'url': url,
            'locked': self.id(),
        })

        d.addCallback(self.get_news_slice, topic, url)

    def get_news_slice(self, result, topic, url):
        if not result:
            log.msg('News slice is empty!')
            return

        edges = result[0]['time'], result[-1]['time']
        d = agent.request('GET', url)
        d.addCallback(self.process_news, topic=topic, url=url, edges=edges)

    def register_ping(self, topic, url, time):
        self.db.ping.insert({
            'topic': topic,
            'url': url,
            'time': time,
            'locked': False,
        }, safe=True)

        d = Deferred()
        d.addCallback(self.get_news, topic=topic, url=url)

        TopicEntryBuffer(topic).put(d)


class TopicEntryBuffer(ParametrizedSingleton):
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
            topic = request.args["hub.topic"][0].strip()
            url = request.args["hub.url"][0].strip()
        except (KeyError):
            return self.mk_response(None, True)

        time = datetime.now()

        Topic(self.db).register_ping(topic=topic, url=url, time=time)

        return self.mk_response(True, None)
