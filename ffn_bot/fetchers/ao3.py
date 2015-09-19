import re
import logging
import itertools

from google import search
from requests import get
from lxml import html
from lxml.cssselect import CSSSelector

from ffn_bot.metaparse import Metaparser, parser
from ffn_bot.cache import get_default_cache
from ffn_bot.bot_tools import safe_int
from ffn_bot.site import Site
from ffn_bot import site

__all__ = ["ArchiveOfOurOwn"]

AO3_LINK_REGEX = re.compile(
    r"http(s)?://([^.]+\.)?archiveofourown.org/works/(?P<sid>\d+)[^ ]*",
    re.IGNORECASE)
AO3_FUNCTION = "linkao3"

AO3_AUTHOR_NAME = '//a[@rel="author"]/text()'
AO3_AUTHOR_URL = '//a[@rel="author"]/@href'
AO3_META_PARTS = '//dl[@class="stats"]//text()'
AO3_TITLE = '//h2/text()'
AO3_SUMMARY_FINDER = '//*[@id="workskin"]//*[@class="summary module" and @role="complementary"]/blockquote//text()'
AO3_DOWNLOAD = '//*[@id="main"]/div[2]/ul/li[5]/ul/li[2]/a/@href'

AO3_FANDOM_TAGS = CSSSelector("dd.fandom ul li").path + "//text()"


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
        return "http://archiveofourown.org/works/%s/" % id

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return self._id_to_link(str(id))

# Filter out direct links.
        match = AO3_LINK_REGEX.match(request)
        if match is not None:
            return request

        return get_default_cache().search(
            request,
            "http://archiveofourown.org/works"
        )

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def get_story(self, query):
        return Story(self.find_link(query, set()))

    def extract_direct_links(self, body, context):
        # for _,_,id in AO3_LINK_REGEX.findall(body):
        #     yield self.generate_response(self.id_to_link(id), context)
        return (
            (
                match.start(0),
                self.generate_response(
                    self._id_to_link(match.group(3)), context
                )
            )
            for match in AO3_LINK_REGEX.finditer(body)
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
        return "http://archiveofourown.org/works/%s?view_adult=true" % AO3_LINK_REGEX.match(
            self.url).groupdict()["sid"]

    def get_url(self):
        return "http://archiveofourown.org/works/%s" % AO3_LINK_REGEX.match(
            self.url).groupdict()["sid"]

    def get_value_from_tree(self, xpath, sep=" "):
        return sep.join(self.tree.xpath(xpath)).strip()

    def parse_html(self):
        page = get_default_cache().get_page(self.get_real_url())
        self.tree = html.fromstring(page)

        self.summary = self.get_value_from_tree(AO3_SUMMARY_FINDER)
        self.title = self.get_value_from_tree(AO3_TITLE)
        self.author = self.get_value_from_tree(AO3_AUTHOR_NAME)
        self.authorlink = self.get_value_from_tree(AO3_AUTHOR_URL)
        self.stats = AO3Metadata(
            AO3_LINK_REGEX.match(self.url).groupdict()["sid"], self.tree)

    def get_site(self):
        return "Archive of Our Own", "http://www.archiveofourown.org/"

    def get_download(self):
        return "http://archiveofourown.org/" + self.get_value_from_tree(
            AO3_DOWNLOAD)
