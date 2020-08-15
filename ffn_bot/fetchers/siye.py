# Sink Into Your Eyes site

import logging
import re

from lxml import html

from ffn_bot import site
from ffn_bot.bot_tools import safe_int
from ffn_bot.cache import default_cache
from ffn_bot.metaparse import Metaparser, parser
from ffn_bot.site import Site

__all__ = ["SinkIntoYourEyes"]

SIYE_LINK_REGEX = re.compile(
    r"http(?:s)?://www\.siye\.co\.uk/viewstory\.php\?sid=(?P<sid>\d+)", re.IGNORECASE)
SIYE_FUNCTION = "linksiye"
SIYE_SEARCH_QUERY = "http://www.siye.co.uk/viewstory.php?sid=%s"

SIYE_AUTHOR_URL = '//html/body/table/tr/td/table/tr[1]/td[1]/h3[1]//@href'
SIYE_SUMMARY_AND_META = '//html/body/table/tr/td/table/tr[2]/td[1]//text()'
SIYE_TITLE_AUTHOR_NAME = '//html/body/table/tr/td/table/tr[1]/td[1]/h3[1]//text()'



class SIYEMetadata(Metaparser):

    @parser
    @staticmethod
    def parse_metadata(id, tree):
        summary_and_meta = ' '.join(tree.xpath(SIYE_SUMMARY_AND_META))
        stats = summary_and_meta
        stats = re.sub("Story Total: ", "",stats.replace("Awards:  View Trophy Room",""))
        if "Story is Complete" in stats:
            stats = re.sub("Story is Complete","Status: Complete", stats)
        else:
            stats = stats + "Status: In Progress"
        stats = stats.split("\n")
        stats = [x for x in stats if x.strip()]
        for l in stats:
            individual_stat = tuple(p.strip() for p in l.split(":", 2))
            if individual_stat[0]!="Summary": # Don't return the summary
                if individual_stat[0]=="Reviews":
                    if individual_stat[1]: # If the reviews stat is not present, don't return it
                        yield individual_stat
                else:
                    yield individual_stat

            

    @parser
    @staticmethod
    def ID(id, tree):
        return id


class SinkIntoYourEyes(Site):

    def __init__(self, regex=SIYE_FUNCTION, name=None):
        super(SinkIntoYourEyes, self).__init__(regex, name)

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
        return "http://www.siye.co.uk/viewstory.php?sid=%s" % id

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return self.id_to_url(id)
        # Filter out direct links.
        match = SIYE_LINK_REGEX.match(request)
        if match is not None:
            return request

        return default_cache.search(SIYE_SEARCH_QUERY % id)

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def extract_direct_links(self, body, context):
        return (
            self.generate_response(self.id_to_url(safe_int(id)), context)
            for id in SIYE_LINK_REGEX.findall(body)
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
        return SinkIntoYourEyes.id_to_url(
            str(SIYE_LINK_REGEX.match(self.url).groupdict()["sid"])
        )

    def parse_html(self):
        self.tree = tree = html.fromstring(default_cache.get_page(self.url))

        self.summary_and_meta = ' '.join(tree.xpath(SIYE_SUMMARY_AND_META))
        self.summary = ''.join(
            re.findall(
                'Summary: (.*?)(?=Hitcount:)',
                self.summary_and_meta,
                re.DOTALL
            )
        ).replace("\n", " ").strip()
        self.stats = SIYEMetadata(
            str(SIYE_LINK_REGEX.match(self.url).groupdict()["sid"]),
            self.tree

        )
        self.title = tree.xpath(SIYE_TITLE_AUTHOR_NAME)[0]
        self.author = tree.xpath(SIYE_TITLE_AUTHOR_NAME)[2]
        self.authorlink = 'http://www.siye.co.uk/' + \
                          tree.xpath(SIYE_AUTHOR_URL)[0]

    def get_site(self):
        return "Sink Into Your Eyes", "http://www.siye.co.uk"
