# encoding: utf-8
import sys
from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log
# from twisted.internet import defer

import txmongo

from sub import SubscribeHandler
from pub import PublishHandler

log.startLogging(sys.stdout)


class Root(Resource):
    isLeaf = False

# mongo connection
db = txmongo.lazyMongoConnectionPool()

# http resources
root = Root()
root.putChild("sub", SubscribeHandler(db.foo))
root.putChild("pub", PublishHandler(db.foo))

reactor.listenTCP(8080, server.Site(root))
reactor.run()
