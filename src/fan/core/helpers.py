# encoding: utf-8

from datetime import datetime
from twisted.internet.protocol import Protocol
from fan.core.rss import RSS
from dateutil.parser import parse

class NewsSender(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def dataReceived(self, bytes):
        pass

    def connectionLost(self, reason):
        self.finished.callback()


class TopicFetcher(Protocol):
    def __init__(self, since, finished):
        self.finished = finished
        self.response = ''
        self.since = since
        # self.left_edge, self.right_edge = edges

    def parse_response(self, data):
        topic = RSS().parse(data)
        for entry in topic.entries:
            entry.pop('updated_parsed')
            updated = parse(entry['updated'])
            yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        generator = self.parse_response(self.response)
        self.finished.callback(generator)
