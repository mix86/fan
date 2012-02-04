# encoding: utf-8

from twisted.web import server
from twisted.web.resource import Resource

from fan.http.sub import SubscribeHandler
from fan.http.pub import PublishHandler
from fan.db import db


def start_sending_timers():
    from fan.core.sub import SendingScheduler
    SendingScheduler(db).start()


def start_ping_timers():
    from fan.core.pub import PingProcessingScheduler
    PingProcessingScheduler(db).start()


def setup_resources():
    class Root(Resource):
        isLeaf = False

    root = Root()
    root.putChild("sub", SubscribeHandler(db))
    root.putChild("pub", PublishHandler(db))
    return root

start_ping_timers()
start_sending_timers()
root = setup_resources()
factory = server.Site(root)
