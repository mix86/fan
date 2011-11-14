# encoding: utf-8

from twisted.internet import reactor

class Controller(object):
    def __init__(self, db, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.db = db

    def id(self):
        return id(self)


class Scheduler(Controller):
    DELAY = 1
    def _run_after_delay(self, ign):
        reactor.callLater(self.DELAY, self.run)

    def run(self):
        raise NotImplemented

