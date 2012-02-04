# encoding: utf-8
import sys

sys.path = [
    '/home/mixael/dev/fan/src',
    '/home/mixael/dev/fan/contrib'
] + sys.path


from twisted.application import service, internet
from fan.http.hub import factory

def getWebService():
    return internet.TCPServer(8080, factory)

application = service.Application("Fan")
service = getWebService()
service.setServiceParent(application)
