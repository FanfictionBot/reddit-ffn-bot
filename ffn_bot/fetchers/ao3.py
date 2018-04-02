import itertools
import logging
import re

from lxml import html
from lxml.cssselect import CSSSelector

from ffn_bot import site
from ffn_bot.bot_tools import safe_int
from ffn_bot.cache import default_cache
from ffn_bot.metaparse import Metaparser, parser
from ffn_bot.site import Site

__all__ = ["ArchiveOfOurOwn"]

AO3_LINK_REGEX = AO3_LINK_REGEX = re.compile(
    r"http(s)?://([^.]+\.)?archiveofourown.org/works/(?P<sid>\d+)[^ ]*",
    re.IGNORECASE)
AO3_FUNCTION = "linkao3"
AO3_SEARCH_QUERY = "site:archiveofourown.org/works/ %s"
AO3_AUTHOR_NAME = '//a[@rel="author"]/text()'
AO3_AUTHOR_URL = '//a[@rel="author"]/@href'
AO3_META_PARTS = '//dl[@class="stats"]//text()'
AO3_TITLE = '//h2/text()'
AO3_SUMMARY_FINDER = '//*[@id="workskin"]//*[@class="summary module" and @role="complementary"]/blockquote//text()'
AO3_FANDOM_TAGS = CSSSelector("dd.fandom ul li").path + "//text()"
AO3_EPUB_DOWNLOAD = './/a[contains(text(),"EPUB")]/@href'
AO3_MOBI_DOWNLOAD = './/a[contains(text(),"MOBI")]/@href'


class AO3Metadata(Metaparser):

    @parser
    @staticmethod
    def parse_fandom(id, tree):
        res = tree.xpath(AO3_FANDOM_TAGS)
        if len(res) > 1:
            yield "Fandoms", ", ".join(res)
        elif len(res) == 0:
            raise site.StoryDoesNotExist
        else:
            yield "Fandom", res[0]

    @parser
    @staticmethod
    def parse_basemeta(id, tree):
        res = tree.xpath(AO3_META_PARTS)

        yield from (
            (k[:-1], v)
            for k, v in itertools.islice(zip(res, res[1:]), None, None, 2)
        )

    @parser
    @staticmethod
    def ID(id, tree):
        return id


class ArchiveOfOurOwn(Site):

    def __init__(self, regex=AO3_FUNCTION, name=None):
        super(ArchiveOfOurOwn, self).__init__(regex, name)

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
            logging.info("FF not found: %s" % request)
            return

        if link is None:
            return

        return self.generate_response(link, context)

    def _id_to_link(self, id):
        return "https://archiveofourown.org/works/%s/" % id

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return self._id_to_link(str(id))

        # Filter out direct links.
        match = AO3_LINK_REGEX.match(request)
        if match is not None:
            return request

        return default_cache.search(AO3_SEARCH_QUERY % request)

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def get_story(self, query):
        return Story(self.find_link(query, set()))

    def extract_direct_links(self, body, context):
        # for _,_,id in AO3_LINK_REGEX.findall(body):
        #     yield self.generate_response(self.id_to_link(id), context)
        return (
            self.generate_response(self._id_to_link(id), context)
            for _, _, id in AO3_LINK_REGEX.findall(body)
        )


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

    def get_real_url(self):
        return "https://archiveofourown.org/works/%s?view_adult=true" % AO3_LINK_REGEX.match(self.url).groupdict()[
            "sid"]

    def get_url(self):
        return "https://archiveofourown.org/works/%s" % AO3_LINK_REGEX.match(self.url).groupdict()["sid"]

    def get_value_from_tree(self, xpath, sep=""):
        return sep.join(self.tree.xpath(xpath)).strip()

    def parse_html(self):
        page = default_cache.get_page(self.get_real_url())
        self.tree = html.fromstring(page)
        self.summary = self.get_value_from_tree(AO3_SUMMARY_FINDER)
        self.title = self.get_value_from_tree(AO3_TITLE)
        self.author = self.get_value_from_tree(AO3_AUTHOR_NAME)
        self.authorlink = "https://www.archiveofourown.org" + self.get_value_from_tree(AO3_AUTHOR_URL)
        self.stats = AO3Metadata(
            AO3_LINK_REGEX.match(self.url).groupdict()["sid"], self.tree)

    def get_site(self):
        return "Archive of Our Own", "https://www.archiveofourown.org/"

    def get_download(self):
        epub_download = "https://archiveofourown.org" + self.get_value_from_tree(AO3_EPUB_DOWNLOAD)
        mobi_download = "https://archiveofourown.org" + self.get_value_from_tree(AO3_MOBI_DOWNLOAD)
        return (epub_download, mobi_download)
