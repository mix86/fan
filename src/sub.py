# encoding: utf-8

import simplejson as json

from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.server import NOT_DONE_YET
from twisted.internet.defer import Deferred

from base import Controller, BaseHandler, Scheduler
from utils import StringProducer
from pub import Topic
from base import NoNews, log_failure


agent = Agent(reactor)


class SendingScheduler(Scheduler):

    def start(self):
        self._run_after_delay(None)

    def run(self):
        d = Deferred()
        subscription = Subscription(self.db)
        d.addCallback(subscription.find)
        d.addCallback(subscription.send_news)
        d.addErrback(log_failure)
        d.addCallback(self._run_after_delay)
        d.callback(None)


class Subscription(Controller):

    def find(self, ign, cb_url=None, topic=None):
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

    def send_news(self, sub_list):
        log.msg('Sending news to %d subscribers' % len(sub_list))
        for sub in sub_list:
            topic = sub['topic']
            cb_url = sub['cb_url']
            since = sub.get('last')
            log.msg('Send topic %(topic)s news' % {'topic': topic})
            if since is None:
                raise NotImplementedError

            d = Topic(db=self.db, topic=topic).find_entries(since=since)
            d.addCallback(self.push_to_subscriber, sub)
            d.addCallback(self.mark_as_sent,
                          topic=topic,
                          cb_url=cb_url)
            d.addErrback(self.catch_nonews)


    def push_to_subscriber(self, entries, sub):

            if not entries:
                raise NoNews

            entries = sorted(entries, key=lambda i: i['time'])

            cb_url = sub['cb_url']

            for item in entries:
                print item['data']['id'], item['time']

            body = StringProducer("data=%s" %
                            json.dumps([e['data'] for e in entries]))

            headers = Headers({
                'Content-Type': ['application/x-www-form-urlencoded'],
            })

            d = agent.request('POST',
                              str(cb_url),
                              headers,
                              body)

            d.addCallback(self.check_response, time=entries[-1]['time'])

            return d

    def check_response(self, response, time):
        if response.code != 200:
            print '*'*80, '\n', response.code, '*'*80
            raise NotImplementedError

        return time

    def catch_nonews(self, failure):
        if failure.check(NoNews):
            log.msg('Nothing to send!')
        else:
            return failure

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


class NewsSender(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def dataReceived(self, bytes):
        pass

    def connectionLost(self, reason):
        self.finished.callback()


class SubscribeHandler(BaseHandler, Resource):

    def render_GET(self, request):
        """Get subscriptions for host"""

        cb_url = request.args.get('hub.callback', [None])[0]
        topic = request.args.get('hub.topic', [None])[0]

        d = Subscription(self.db).find(cb_url=cb_url, topic=topic)
        d.addCallback(self._success, request)
        d.addErrback(self._failure, request)

        return NOT_DONE_YET

    def render_POST(self, request):
        mode = request.args['hub.mode'][0]
        cb_url = request.args.get('hub.callback', [None])[0]
        topic = request.args.get('hub.topic', [None])[0]

        if mode == 'subscribe':
            Subscription(self.db).create(cb_url=cb_url,
                                         topic=topic)

        elif mode == 'unsubscribe':
            Subscription(self.db).remove(cb_url=cb_url,
                                         topic=topic)

        else:
            raise NotImplementedError

        return self.mk_response(True, None)

