# encoding: utf-8

from twisted.python import log
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.internet.defer import Deferred

from fan.core.base import Controller, Scheduler
from fan.core.fail import NoNews, log_failure
from fan.core.helpers import TopicFetcher
from fan import settings
from fan.utils import smart_str

agent = Agent(reactor)

class PingProcessingScheduler(Scheduler):
    """Таймер запускаючищий процесс обработки пингов"""
    DELAY = settings.FETCHING_DELAY

    def start(self):
        self._run_after_delay(None)

    def run(self):
        d = self.select_topics()
        d.addCallback(self.process_pings)
        d.addCallback(self._run_after_delay)

    def select_topics(self):
        return self.db.ping.group(
            condition={'locked': False},
            key=['topic', 'url'],
            reduce='function(doc, out){}',
            initial={}
        )

    def process_pings(self, result):
        """
        Запускает обработку пингов для каждого топика
        """
        if not len(result):
            log.msg("No pings found")
            return

        for topic_params in result:
            topic = Topic(db=self.db, **topic_params)
            d = Deferred()
            d.addCallback(topic.lock)
            d.addCallback(topic.update)
            d.addCallbacks(topic.create_entries, topic.nothing_to_update)
            d.addCallback(topic.clean_pings)
            d.addErrback(log_failure)
            d.callback(None)


class Topic(Controller):
    def __init__(self, topic, url=None, *args, **kwargs):
        super(Topic, self).__init__(*args, **kwargs)
        self.topic = topic
        self.url = smart_str(url)

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

        d = self.db.topic.find_one({
            'topic': self.topic,
            # 'url': self.url,
            # 'locked': self.id(),
        }, sort=[('time', -1)])

        return d

    def unlock(self, failure):
        """
        Разблокирует пинги (по сути откат)
        """
        log.msg('Can\'n fetch topic! I\'ll try later')
        self.db.ping.update({
            'topic': self.topic,
            'url': self.url,
            'locked': self.id(),
        }, {
            '$set': {'locked': False},
        }, multi=True, safe=True)

        return failure

    def clean_pings(self, ign):
        log.msg('Delete old pings')
        self.db.ping.remove({
            'topic': self.topic,
            'url': self.url,
            'locked': self.id(),
        })

    def update(self, result):
        """
        Обновляет топик. Если обновлять нечего,
        поднимает исключение NoNews
        """
        if not result:
            raise NoNews

        since = result[0]['time'].strftime('%Y-%m-%dT%H:%M:%S') #TODO: указывать TZ
        d = agent.request('GET', "%s?since=%s" % (self.url, since))
        d.addCallback(self.fetch, since=since)
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

    def fetch(self, response, since):
        """
        Скачивает обновления топика
        """
        finished = Deferred()
        response.deliverBody(TopicFetcher(since=since, finished=finished))
        return finished

    def create_entries(self, generator):
        """
        Сохраняет обновления топика
        """
        i = 0
        for entry, updated in generator:
            record = {
                'topic': self.topic,
                'url': self.url,
                'data': entry,
                'time': updated,
            }
            self.db.topic.update(
                record,
                {'$set': record},
                upsert=True, safe=True)
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
        """Регистрирует пинг"""
        self.db.ping.insert({
            'topic': self.topic,
            'url': self.url,
            'time': time,
            'locked': False,
        }, safe=True)


