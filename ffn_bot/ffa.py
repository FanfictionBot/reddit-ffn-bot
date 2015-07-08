# Harry Potter Fanfic Archive site

import re
import logging
import requests

from google import search
from requests import get
from lxml import html

from ffn_bot.cache import default_cache
from ffn_bot.bot_tools import safe_int
from ffn_bot.site import Site
from ffn_bot import site


__all__ = ["HPFanfictionArchive"]

FFA_LINK_REGEX = re.compile(
    r"http(s)?://www.hpfanficarchive.com/stories/viewstory.php?sid=(?P<sid>\d+)", re.IGNORECASE)
FFA_FUNCTION = "linkffa"
FFA_SEARCH_QUERY = "http://www.hpfanficarchive.com/stories/viewstory.php?sid= %s"

FFA_AUTHOR_NAME = '//*[@id="pagetitle"]/a[2]/text()'
FFA_AUTHOR_URL = '//*[@id="pagetitle"]/a[2]/@href'
FFA_SUMMARY_AND_META = '//*[@id="mainpage"]/div[4]//text()'
FFA_TITLE = '//*[@id="pagetitle"]/a[1]/text()'


class HPFanfictionArchive(Site):

    def __init__(self, regex=FFA_FUNCTION + r"\((.*?)\)", name=None):
        super(HPFanfictionArchive, self).__init__(regex, name)

    def from_requests(self, requests, context):
        _pitem = []
        item = _pitem
        for request in requests:
            try:
                item = self.process(request, context)
            except Exception as e:
                continue

            if item is not None:
                yield item
        # Make sure we yield something.
        yield ""

    def process(self, request, context):
        try:
            link = self.find_link(request, context)
        except IOError as e:
            logging.error("FF not found: %s" % request)
            return

        if link is None:
            return

        return self.generate_response(link, context)

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return "http://www.hpfanficarchive.com/stories/viewstory.php?sid=%d" % id

        # Filter out direct links.
        match = FFA_LINK_REGEX.match(request)
        if match is not None:
            return request

        return default_cache.search(FFA_SEARCH_QUERY % request)

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def get_story(self, query):
        return Story(self.find_link(query, set()))


class Story(site.Story):

    def __init__(self, url, context=None):
        super(Story, self).__init__(context)
        self.url = url
        self.raw_stats = []

        self.stats = ""
        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""
        self.summary_and_meta = ""
        self.parse_html()

    def parse_html(self):
        tree = html.fromstring(default_cache.get_page(self.url))

        self.summary_and_meta = ''.join(tree.xpath(FFA_SUMMARY_AND_META))
        self.summary = ''.join(re.findall('Summary: (.*?)\n', self.summary_and_meta))
        self.make_stats()
        self.title = tree.xpath(FFA_TITLE)[0]
        self.author = tree.xpath(FFA_AUTHOR_NAME)[0]
        self.authorlink = 'http://www.hpfanficarchive.com/stories/' + \
            tree.xpath(FFA_AUTHOR_URL)[0]

        print(self.summary)
        print(self.stats)

    def make_stats(self):
        self.stats = self.summary_and_meta.split("Rated: ")
        self.stats[1] = "Rated: " + self.stats[1]
        self.stats = self.stats[1]
        self.stats.replace("\n\n", "\n")
        self.stats.replace("\n\n\n", "\n")
        self.stats.replace("\n", "\n\n")
        self.stats.replace("  ", " ")
        self.stats.replace("   ", " ")
