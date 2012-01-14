# encoding: utf-8
from datetime import datetime
import PyRSS2Gen
import feedparser

class RSS(object):
    def generate(self, entries):
        topic = entries[0]['topic']
        url = entries[0]['url']
        rss = PyRSS2Gen.RSS2(
            title=topic,
            link=url,
            description=topic,
            lastBuildDate=datetime.now(),
            items=[
                PyRSS2Gen.RSSItem(
                    title=entry['data']['title'],
                    link=entry['data']['link'],
                    description=entry['data']['summary'],
                    guid=entry['data']['id'],
                    pubDate=entry['data']['updated'],
                 )
                for entry in entries
            ])

        return rss.to_xml()

    def parse(self, xml):
        return feedparser.parse(xml)
