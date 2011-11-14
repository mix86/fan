# encoding: utf-8
import sys

sys.path.append('/home/mixael/dev/pubsub_proto/src')
from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log

import txmongo

from fan.http.sub import SubscribeHandler
from fan.http.pub import PublishHandler

log.startLogging(sys.stdout)

# mongo connection
db = txmongo.lazyMongoConnectionPool()

db_foo = db.foo

def start_sending_timers():
    from fan.core.sub import SendingScheduler
    SendingScheduler(db_foo).start()


def start_ping_timers():
    from fan.core.pub import PingProcessingScheduler
    PingProcessingScheduler(db_foo).start()


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
