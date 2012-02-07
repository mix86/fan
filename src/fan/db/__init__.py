# encoding: utf-8

import pymongo
from twisted.internet.threads import deferToThread
from fan import settings

COLLECTIONS = 'topic', 'ping', 'sub'


class AsyncCollection(object):
    def __init__(self, db, name):
        super(AsyncCollection, self).__init__()
        self._proxy = db[name]
        self._db = db
        self._name = name

    def find(self, *args, **kwargs):
        d = deferToThread(self._proxy.find, *args, **kwargs)
        d.addCallback(list)
        return d

    def insert(self,  *args, **kwargs):
        return self._proxy.insert(*args, **kwargs)

    def update(self,  *args, **kwargs):
        return self._proxy.update(*args, **kwargs)

    def remove(self,  *args, **kwargs):
        return self._proxy.remove(*args, **kwargs)

    def group(self,  *args, **kwargs):
        return deferToThread(self._proxy.group, *args, **kwargs)


class AsyncDB(object):
    def __init__(self, db):
        super(AsyncDB, self).__init__()
        self._db = db

    def __getattribute__(self, name):
        if name in COLLECTIONS:
            return AsyncCollection(db=self._db, name=name)

        return super(AsyncDB, self).__getattribute__(name)


con = pymongo.ReplicaSetConnection(','.join(settings.DB['HOSTS']), replicaSet=settings.DB['REPLICASET'])
db = AsyncDB(getattr(con, settings.DB['NAME']))
