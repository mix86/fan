# encoding: utf-8
import sys
try:
    import settings
except ImportError:
    from fan import settings

sys.path = settings.PATH + sys.path

from twisted.application import service, internet
from fan.http.hub import factory

application = service.Application("Fan")
service = internet.TCPServer(8080, factory)
service.setServiceParent(application)

print 'Fan hub started with settings:', ', '.join('%s=%s' % (attr, getattr(settings, attr))
          for attr in dir(settings) if attr == attr.upper())
