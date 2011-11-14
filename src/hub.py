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

# mongo connection
db = txmongo.lazyMongoConnectionPool()

db_foo = db.foo

def start_sending_timers():
    from sub import SendingTimer
    SendingTimer(db_foo).start()


def start_ping_timers():
    from pub import PingProcessingTimer
    PingProcessingTimer(db_foo).start()


class Root(Resource):
    isLeaf = False


# http resources
root = Root()
root.putChild("sub", SubscribeHandler(db_foo))
root.putChild("pub", PublishHandler(db_foo))

reactor.listenTCP(8080, server.Site(root))


start_ping_timers()
start_sending_timers()
reactor.run()
