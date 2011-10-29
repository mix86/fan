# encoding: utf-8

import simplejson as json

from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.server import NOT_DONE_YET

from base import BaseHandler
from utils import StringProducer
from pub import Topic

agent = Agent(reactor)

def send_foo(db):
    #TODO: переделать на получение подписок из db.sub
    Subscription(db).send_news(topic='foo')
    reactor.callLater(1, send_foo, db)

class Subscription(object):
    def __init__(self, db):
        super(Subscription, self).__init__()
        self.db = db
        self._db = db.sub

    def find(self, cb_url=None, topic=None):
        q = {}

        if cb_url:
            q.update({"cb_url": cb_url})

        if topic:
            q.update({"topic": topic})

        d = self._db.find(q)

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

    def send_news(self, topic):
        log.msg('Send news called for %s' % topic)
        d = self.find(topic=topic)
        d.addCallback(self._really_send_news, topic)

    def _really_send_news(self, sub_list, topic):
        log.msg('Sending news to %d subscribers' % len(sub_list))
        for sub in sub_list:
            since = sub.get('last')
            if since is None:
                raise NotImplementedError

            d = Topic(db=self.db, topic=topic).find_entries(since=since)
            d.addCallback(self.send_news_to_subscriber, sub)


    def send_news_to_subscriber(self, entries, sub):

            if not entries:
                print 'No entries'
                return

            entries = sorted(entries, key=lambda i: i['time'])

            cb_url = sub['cb_url']
            topic = sub['topic']

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

            d.addCallback(self.mark_as_sent,
                          topic=topic,
                          cb_url=cb_url,
                          time=entries[-1]['time'])


    def mark_as_sent(self, response, topic, cb_url, time):
        if response.code != 200:
            print '*'*80, '\n', response.code, cb_url, '*'*80
            raise NotImplementedError

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

