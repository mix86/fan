# encoding: utf-8

from datetime import datetime
from twisted.internet.protocol import Protocol
from fan.core.rss import RSS

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
        topic = RSS().parse(data)
        for entry in topic.entries:
            updated_parsed = entry.pop('updated_parsed')
            try:
                updated = datetime.strptime(entry['updated'],
                                            '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                updated = datetime(updated_parsed.tm_year,
                                   updated_parsed.tm_mon,
                                   updated_parsed.tm_mday,
                                   updated_parsed.tm_hour,
                                   updated_parsed.tm_min,
                                   updated_parsed.tm_sec)

            yield entry, updated

    def dataReceived(self, bytes):
        self.response += bytes

    def connectionLost(self, reason):
        generator = self.parse_response(self.response)
        self.finished.callback(generator)
