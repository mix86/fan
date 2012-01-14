# encoding: utf-8

from datetime import datetime
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.python import log

from fan.core.base import Controller
from fan.core.fail import NoNews
from fan.core.pub import Topic
from fan.utils import AtomFeedProducer

agent = Agent(reactor)

class Distributor(Controller):
    def __init__(self, subscription, *args, **kwargs):
        super(Distributor, self).__init__(*args, **kwargs)
        self.subscription = subscription

    def distribute(self, sub_list):
        # print sub_list
        log.msg('Sending news to %d subscribers' % len(sub_list))
        for sub in sub_list:
            topic = sub['topic']
            cb_url = sub['cb_url']
            since = sub.get('last', datetime(1970, 1, 1))
            log.msg('Send topic %(topic)s news' % {'topic': topic})
            if since is None:
                raise NotImplementedError, 'since in None'

            d = Topic(db=self.db, topic=topic).find_entries(since=since)
            d.addCallback(self.push, sub)
            d.addCallback(self.subscription.mark_as_sent,
                          topic=topic,
                          cb_url=cb_url)
            d.addErrback(self.catch_nonews)

    def push(self, entries, sub):

            if not entries:
                raise NoNews

            entries = sorted(entries, key=lambda i: i['time'])

            cb_url = sub['cb_url']

            last_entry_time = entries[-1]['time']

            headers = Headers({
                # 'Content-Type': ['appication/x-www-form-urlencoded'],
                # 'Content-Type': ['application/json'],
                'Content-Type': ['text/xml'],
            })

            body = AtomFeedProducer(entries)

            d = agent.request('POST', str(cb_url), headers, body)

            d.addCallback(self.check_response, time=last_entry_time)

            return d

    def check_response(self, response, time):
        if response.code != 200:
            raise NotImplementedError('response code: %s' % response.code)

        return time

    def catch_nonews(self, failure):
        if failure.check(NoNews):
            log.msg('Nothing to send!')
        else:
            return failure
