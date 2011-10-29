# encoding: utf-8

from datetime import datetime

import feedparser
from twisted.web.resource import Resource
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.error import AlreadyCalled
from twisted.web.client import Agent
from twisted.internet.defer import Deferred

from base import Controller, ParametrizedSingleton, BaseHandler

agent = Agent(reactor)


class NewsFetcher(Protocol):
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
    def __init__(self, topic, url=None, *args, **kwargs):
        super(Topic, self).__init__(*args, **kwargs)
        self.topic = topic
        self.url = url

    def create_entries(self, generator):
        i = 0
        for entry, updated in generator:
            self.db.topic.insert({
                'topic': self.topic,
                'url': self.url,
                'data': entry,
                'time': updated,
            }, safe=True)
            i += 1

        log.msg('Fetched %(i)d entries in topic %(topic)s' % {
            'i': i,
            'topic': self.topic,
        })

    def find_entries(self, since):
        d = self.db.topic.find({
            'topic': self.topic,
            'time': {'$gt': since},
        })

        return d

    def get_news(self, ign):

        self.db.ping.update({
            'topic': self.topic,
            'url': self.url,
            'locked': False,
        }, {
            '$set': {'locked': self.id()},
        }, multi=True, safe=True)

        d = self.db.ping.find({
            'topic': self.topic,
            'url': self.url,
            'locked': self.id(),
        })

        d.addCallback(self.get_news_slice)

    def get_news_slice(self, result):
        if not result:
            log.msg('News slice is empty!')
            return

        edges = result[0]['time'], result[-1]['time']
        d = agent.request('GET', self.url)
        d.addCallback(self.process_news_slice, edges=edges)

    def process_news_slice(self, response, edges):
        finished = Deferred()
        finished.addCallback(self.create_entries)
        response.deliverBody(NewsFetcher(edges=edges, finished=finished))
        return finished

    def register(self, time):
        self.db.ping.insert({
            'topic': self.topic,
            'url': self.url,
            'time': time,
            'locked': False,
        }, safe=True)

        d = Deferred()
        d.addCallback(self.get_news)

        TopicBuffer(self.topic).put(d)


class TopicBuffer(ParametrizedSingleton):
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
        except KeyError, e:
            return self.mk_response(None, e)

        Topic(db=self.db, topic=topic, url=url).register(time=datetime.now())

        return self.mk_response(True, None)
