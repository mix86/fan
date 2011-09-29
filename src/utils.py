# encoding: utf-8

def norm(val):
    if isinstance(val, dict):
        for k in val:
            val[k] = norm(val[k])
    elif isinstance(val, list):
        i = 0
        for v in val:
            val[i] = norm(v)
    elif isinstance(val, (basestring, int, float, long)):
        pass
    elif val is None:
        pass
    else:
        val = unicode(val)

    return val


from zope.interface import implements

from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass
