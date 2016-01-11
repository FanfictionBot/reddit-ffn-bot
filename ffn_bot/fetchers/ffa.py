# Harry Potter Fanfic Archive site

import re
import logging

from lxml import html

from ffn_bot.cache import get_default_cache
from ffn_bot.bot_tools import safe_int
from ffn_bot.site import Site
from ffn_bot import site
from ffn_bot.metaparse import Metaparser, parser

__all__ = ["HPFanfictionArchive"]

FFA_LINK_REGEX = re.compile(
    r"http(?:s)?://www\.hpfanficarchive\.com/stories/viewstory\.php\?sid=(?P<sid>\d+)", re.IGNORECASE)
FFA_FUNCTION = "linkffa"
FFA_SEARCH_SITE = "http://www.hpfanficarchive.com/stories/viewstory.php?sid="

FFA_AUTHOR_NAME = '//*[@id="pagetitle"]/a[2]/text()'
FFA_AUTHOR_URL = '//*[@id="pagetitle"]/a[2]/@href'
FFA_SUMMARY_AND_META = '//*[@id="mainpage"]/div[4]//text()'
FFA_TITLE = '//*[@id="pagetitle"]/a[1]/text()'

FFA_SPLITTER_REGEX = re.compile(
    "[A-Z][a-z ]*?[a-z]*?:.*?(?=\s*[A-Z](?:[a-z ]*?[a-z]*?:))"
)


class FFAMetadata(Metaparser):

    @parser
    @staticmethod
    def parse_metadata(id, tree):
        summary_and_meta = ' '.join(tree.xpath(FFA_SUMMARY_AND_META))
        stats = summary_and_meta.split("Rated: ")
        stats[1] = "Rated: " + stats[1]
        stats = stats[1]
        stats = re.sub("\s+", " ", stats.replace("\n", " "))
        stats = FFA_SPLITTER_REGEX.findall(stats)
        for l in stats:
            yield tuple(p.strip() for p in l.split(":", 2))

    @parser
    @staticmethod
    def ID(id, tree):
        return id


class HPFanfictionArchive(Site):

    def __init__(self, regex=FFA_FUNCTION, name=None):
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

    def process(self, request, context):
        try:
            link = self.find_link(request, context)
        except IOError as e:
            logging.error("FF not found: %s" % request)
            return

        if link is None:
            return

        return self.generate_response(link, context)

    @staticmethod
    def id_to_url(id):
        return "http://www.hpfanficarchive.com/stories/viewstory.php?sid=%s" % id

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return self.id_to_url(id)
        # Filter out direct links.
        match = FFA_LINK_REGEX.match(request)
        if match is not None:
            return request

        return get_default_cache().search(request, FFA_SEARCH_SITE)

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def extract_direct_links(self, body, context):
        return (
            (
                match.start(0),
                self.generate_response(self.id_to_url(safe_int(id)), context)
            )
            for match in FFA_LINK_REGEX.finditer(body)
        )

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

    def get_url(self):
        return HPFanfictionArchive.id_to_url(
            str(FFA_LINK_REGEX.match(self.url).groupdict()["sid"])
        )

    def parse_html(self):
        self.tree = tree = html.fromstring(
            get_default_cache().get_page(self.url))

        self.summary_and_meta = ' '.join(tree.xpath(FFA_SUMMARY_AND_META))
        self.summary = ''.join(
            re.findall(
                'Summary: (.*?)(?=Rated:)',
                self.summary_and_meta,
                re.DOTALL
            )
        ).replace("\n", " ").strip()
        self.stats = FFAMetadata(
            str(FFA_LINK_REGEX.match(self.url).groupdict()["sid"]),
            self.tree

        )
        self.title = tree.xpath(FFA_TITLE)[0]
        self.author = tree.xpath(FFA_AUTHOR_NAME)[0]
        self.authorlink = 'http://www.hpfanficarchive.com/stories/' + \
            tree.xpath(FFA_AUTHOR_URL)[0]

    def get_site(self):
        return "HP Fanfic Archive", "http://www.hpfanficarchive.com"
