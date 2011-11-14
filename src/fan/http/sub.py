# encoding: utf-8

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from fan.http.base import BaseHandler

from fan.core import Subscription

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

