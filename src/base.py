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


class Controller(object):
    def __init__(self, db, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.db = db

    def id(self):
        return id(self)


class ParametrizedSingleton(object):
    def __new__(cls, param, *args, **kwargs):
        try:
            if param in cls._instances:
                return cls._instances[param]
        except AttributeError:
            cls._instances = {}

        instance = super(ParametrizedSingleton, cls).__new__(cls, *args, **kwargs)
        cls._instances[param] = instance
        return instance

