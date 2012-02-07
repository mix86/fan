# encoding: utf-8

import pymongo
from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from time import sleep
from fan import settings

COLLECTIONS = 'topic', 'ping', 'sub'

#TODO: сделать декоратором
def retry_async(failure, func, *args, **kwargs):
    print 'Exception catched, retry...', failure.getErrorMessage()
    return reactor.callLater(settings.DB['RETRY_DELAY'],
                             func,
                             *args,
                             **kwargs)

def retry_sync(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception, e:
                print 'Exception catched, retry...', e
                #XXX Ужос ужос. нужно срочно переписать все на deferd
                sleep(settings.DB['RETRY_DELAY'])
    return wrapper

class AsyncCollection(object):
    def __init__(self, db, name):
        super(AsyncCollection, self).__init__()
        self._proxy = db[name]
        self._db = db
        self._name = name

    def find(self, *args, **kwargs):
        d = deferToThread(self._proxy.find, *args, **kwargs)
        d.addCallback(list)
        d.addErrback(retry_async, self.find, *args, **kwargs)
        return d

    @retry_sync
    def insert(self,  *args, **kwargs):
        return self._proxy.insert(*args, **kwargs)

    @retry_sync
    def update(self,  *args, **kwargs):
        return self._proxy.update(*args, **kwargs)

    @retry_sync
    def remove(self,  *args, **kwargs):
        return self._proxy.remove(*args, **kwargs)

    def group(self,  *args, **kwargs):
        d = deferToThread(self._proxy.group, *args, **kwargs)
        d.addErrback(retry_async, self.group, *args, **kwargs)
        return d


class AsyncDB(object):
    def __init__(self, db):
        super(AsyncDB, self).__init__()
        self._db = db

    def __getattribute__(self, name):
        if name in COLLECTIONS:
            return AsyncCollection(db=self._db, name=name)

        return super(AsyncDB, self).__getattribute__(name)


# con = pymongo.ReplicaSetConnection(','.join(settings.DB['HOSTS']), replicaSet=settings.DB['REPLICASET'])
con = pymongo.Connection(
    ','.join(settings.DB['HOSTS']),
    replicaSet=settings.DB['REPLICASET']
)
db = AsyncDB(getattr(con, settings.DB['NAME']))
