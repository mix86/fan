# encoding: utf-8

from datetime import datetime

from twisted.web.resource import Resource

from fan.http.base import BaseHandler
from fan.core import Topic

class PublishHandler(BaseHandler, Resource):
    def render_POST(self, request):
        try:
            topic = request.args["hub.topic"][0].strip()
            url = request.args["hub.url"][0].strip()
        except KeyError, e:
            return self.mk_response(None, e)

        Topic(db=self.db, topic=topic, url=url).register(time=datetime.now())

        return self.mk_response(True, None)
