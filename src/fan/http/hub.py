# encoding: utf-8
import sys

from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log

# import txmongo

from fan.http.sub import SubscribeHandler
from fan.http.pub import PublishHandler
from fan.db import db

log.startLogging(sys.stdout)

# mongo connection
# db = txmongo.lazyMongoConnectionPool()

# db = db.fan

def start_sending_timers():
    from fan.core.sub import SendingScheduler
    SendingScheduler(db).start()


def start_ping_timers():
    from fan.core.pub import PingProcessingScheduler
    PingProcessingScheduler(db).start()


class Root(Resource):
    isLeaf = False


# http resources
root = Root()
root.putChild("sub", SubscribeHandler(db))
root.putChild("pub", PublishHandler(db))

# reactor.listenTCP(8080, server.Site(root))

start_ping_timers()
start_sending_timers()
# reactor.run()

factory = server.Site(root)
