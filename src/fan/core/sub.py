# encoding: utf-8

from datetime import datetime

from twisted.python import log
from twisted.internet.defer import Deferred

from fan.core.base import Controller, Scheduler
from fan.core.fail import log_failure
from fan.core.distribute import Distributor
from fan import settings

class SendingScheduler(Scheduler):
    DELAY = settings.SENDING_DELAY

    def start(self):
        self._run_after_delay(None)

    def run(self):
        d = Deferred()

        subscription = Subscription(self.db)
        distributor = Distributor(db=self.db, subscription=subscription)

        d.addCallback(subscription.find)
        d.addCallback(distributor.distribute)
        d.addErrback(log_failure)
        d.addCallback(self._run_after_delay)
        d.callback(None)


class Subscription(Controller):

    def find(self, ign=None, cb_url=None, topic=None):
        q = {}

        if cb_url:
            q.update({"cb_url": cb_url})

        if topic:
            q.update({"topic": topic})

        d = self.db.sub.find(q)

        return d

    def create(self, cb_url, topic):

        self.db.sub.update({
            'topic': topic,
            'cb_url': cb_url,
        }, {
            '$set': {
                'topic': topic,
                'cb_url': cb_url,
                'last': datetime.now()
            },
        }, upsert=True, safe=True)

        log.msg('Host %(cb_url)s subscribed on %(topic)s\n' % {
            'cb_url': cb_url,
            'topic': topic,
        })

    def remove(self, cb_url, topic):
        self.db.sub.remove({'cb_url': cb_url, 'topic': topic})
        log.msg('Subscribtions of %(cb_url)s on %(topic)s removed\n' % {
            'cb_url': cb_url,
            'topic': topic,
        })

    def mark_as_sent(self, time, topic, cb_url):
        assert time, 'Time is none!!!'

        self.db.sub.update({
            "topic": topic,
            'cb_url': cb_url,
        }, {
            '$set': {"last": time},
        })
        log.msg('Topic %(topic)s marked as sent for %(cb_url)s at %(time)s'
                                                                    % vars())
