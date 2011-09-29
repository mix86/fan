# encoding: utf-8
import sys
from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log

log.startLogging(sys.stdout)


class Root(Resource):
    isLeaf = True
    def render_GET(self, request):
        return 'OK'

    def render_POST(self, request):
    	assert request.args
    	print request.args.values()
        return 'OK'


reactor.listenTCP(9998, server.Site(Root()))
reactor.listenTCP(9999, server.Site(Root()))
reactor.run()
