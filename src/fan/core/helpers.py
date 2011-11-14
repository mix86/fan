# encoding: utf-8

import feedparser
from datetime import datetime
from twisted.internet.protocol import Protocol

class NewsSender(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def dataReceived(self, bytes):
        pass

    def connectionLost(self, reason):
        self.finished.callback()


class TopicFetcher(Protocol):
    def __init__(self, edges, finished):
        self.finished = finished
        self.response = ''
        self.left_edge, self.right_edge = edges

    def parse_response(self, data):
        topic = feedparser.parse(data)
        for entry in topic.entries:
            entry.pop('updated_parsed')
            #TODO: feedprser date parse
            updated = datetime.strptime(entry['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if self.left_edge <= updated <= self.right_edge or 1: #TODO: убрать
                yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        generator = self.parse_response(self.response)
        self.finished.callback(generator)
