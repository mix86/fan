# encoding: utf-8

import simplejson as json
from twisted.web.resource import Resource
from twisted.internet import reactor

from utils import norm

class BaseHandler(object):
    isLeaf = True
    def __init__(self, db):
        self.db = db
        Resource.__init__(self)

    def mk_response(self, value, error):

        return json.dumps({
            'success': norm(value),
            'error': unicode(error),
        }) + '\n'

    def _success(self, value, request):
        request.write(self.mk_response(value, None))
        request.finish()

    def _failure(self, error, request):
        request.setResponseCode(500, "Internal server error")
        request.write(self.mk_response(None, error))
        request.finish()


class Controller(object):
    def __init__(self, db, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.db = db

    def id(self):
        return id(self)


class Scheduler(Controller):
    def _run_after_delay(self, ign):
        reactor.callLater(1, self.run)

    def run(self):
        raise NotImplemented


class NoNews(Exception):
    pass

def log_failure(failure):
    log.msg(failure.getErrorMessage())

