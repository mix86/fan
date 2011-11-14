# encoding: utf-8

from datetime import datetime

import feedparser
from twisted.web.resource import Resource
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.internet.defer import Deferred

from base import Controller, BaseHandler, Scheduler
from base import NoNews, log_failure

agent = Agent(reactor)

class PingProcessingScheduler(Scheduler):

    def start(self):
        self._run_after_delay(None)

    def run(self):
        d = self.select_topics()
        d.addCallback(self.process_pings)
        d.addCallback(self._run_after_delay)

    def select_topics(self):
        return self.db.ping.group(
            condition={'locked': False},
            keys=['topic', 'url'],
            reduce='function(doc, out){}',
            initial={}
        )

    def process_pings(self, result):
        if not result['count']:
            print "Nothing to process"
            return

        for topic_params in result['retval']:
            topic = Topic(db=self.db, **topic_params)
            d = Deferred()
            d.addCallback(topic.lock)
            d.addCallback(topic.update)
            d.addCallbacks(topic.create_entries, topic.nothing_to_update)
            d.addErrback(log_failure)
            d.callback(None)


class TopicFetcher(Protocol):
    def __init__(self, edges, finished):
        self.finished = finished
        self.response = ''
        self.left_edge, self.right_edge = edges

    def parse_response(self, data):
        topic = feedparser.parse(data)
        for entry in topic.entries:
            entry.pop('updated_parsed')
            #TODO: feedprser date parse
            updated = datetime.strptime(entry['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if self.left_edge <= updated <= self.right_edge or 1: #TODO: убрать
                yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        generator = self.parse_response(self.response)
        self.finished.callback(generator)


class Topic(Controller):
    def __init__(self, topic, url=None, *args, **kwargs):
        super(Topic, self).__init__(*args, **kwargs)
        self.topic = topic
        self.url = str(url)

    def lock(self, ign):
        """
        Блокирует все доступные пинги данного топика и
        возвращает их список
        """
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

        return d

    def unlock(self, failure):
        """
        Разблокирует пинги (по сути откат)
        """
        print 'UNLOCK!!!!!!!!!!!'
        self.db.ping.update({
            'topic': self.topic,
            'url': self.url,
            'locked': self.id(),
        }, {
            '$set': {'locked': False},
        }, multi=True, safe=True)

        return failure

    def update(self, result):
        """
        Обновляет топик. Если обновлять нечего,
        поднимает исключение NoNews
        """
        if not result:
            raise NoNews

        edges = result[0]['time'], result[-1]['time']
        d = agent.request('GET', self.url)
        d.addCallback(self.fetch, edges=edges)
        d.addErrback(self.unlock)
        return d

    def nothing_to_update(self, failure):
        """
        Перехватывает исключение NoNews
        """
        if failure.check(NoNews):
            log.msg('News slice is empty!')
        else:
            return failure

    def fetch(self, response, edges):
        """
        Скачивает обновления топика
        """
        finished = Deferred()
        response.deliverBody(TopicFetcher(edges=edges, finished=finished))
        return finished

    def create_entries(self, generator):
        """
        Сохраняет обновления топика
        """
        i = 0
        for entry, updated in generator:
            self.db.topic.insert({
                'topic': self.topic,
                'url': self.url,
                'data': entry,
                'time': updated,
            }, safe=True)
            i += 1

        log.msg('Created %(i)d entries in topic %(topic)s' % {
            'i': i,
            'topic': self.topic,
        })

    def find_entries(self, since):
        d = self.db.topic.find({
            'topic': self.topic,
            'time': {'$gt': since},
        })

        return d

    def register(self, time):
        self.db.ping.insert({
            'topic': self.topic,
            'url': self.url,
            'time': time,
            'locked': False,
        }, safe=True)


class PublishHandler(BaseHandler, Resource):
    def render_POST(self, request):
        try:
            topic = request.args["hub.topic"][0].strip()
            url = request.args["hub.url"][0].strip()
        except KeyError, e:
            return self.mk_response(None, e)

        Topic(db=self.db, topic=topic, url=url).register(time=datetime.now())

        return self.mk_response(True, None)
