# encoding: utf-8

from twisted.python import log
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.internet.defer import Deferred

from fan.core.base import Controller, Scheduler
from fan.core.fail import NoNews, log_failure
from fan.core.helpers import TopicFetcher
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


