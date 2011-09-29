# encoding: utf-8

import simplejson as json
from twisted.web.resource import Resource
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


