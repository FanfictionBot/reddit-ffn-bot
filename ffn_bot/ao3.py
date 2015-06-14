import re
import logging

from google import search
from requests import get
from lxml import html

from ffn_bot.site import Site
from ffn_bot import site

__all__ = ["ArchiveOfOurOwn"]

AO3_LINK_REGEX = re.compile(r"http(s)?://([^.]+\.)?archiveofourown.org/works/(?P<sid>\d+).*", re.IGNORECASE)
AO3_FUNCTION = "linkao3"
AO3_SEARCH_QUERY = "site:archiveofourown.org/works/ %s"

AO3_AUTHOR_NAME = '//a[@rel="author"]/text()'
AO3_AUTHOR_URL = '//a[@rel="author"]/@href'
AO3_META_PARTS = '//dl[@class="stats"]//text()'
AO3_TITLE = '//h2/text()'
AO3_SUMMARY_FINDER = '//*[@id="workskin"]//*[@role="complementary"]//blockquote//text()'


class ArchiveOfOurOwn(Site):

    def __init__(self, regex=AO3_FUNCTION + r"\((.*?)\)", name=None):
        super(ArchiveOfOurOwn, self).__init__(regex, name)

    @staticmethod
    def safe_int(value):
        try:
            return int(value)
        except ValueError:
            return None

    def from_requests(self, requests):
        _pitem = []
        item = _pitem
        for request in requests:
            try:
                item = self.process(request)
            except Exception as e:
                continue

            if item is not None:
                yield item
        # Make sure we yield something.
        yield ""

    def process(self, request):
        try:
            link = self.find_link(request)
        except IOError as e:
            logging.info("FF not found: %s" % request)
            return

        if link is None:
            return

        return self.generate_response(link)

    def find_link(self, request):
        # Find link by ID.
        id = ArchiveOfOurOwn.safe_int(request)
        if id is not None:
            return "http://archiveofourown.org/works/%d/" % id

        # Filter out direct links.
        match = AO3_LINK_REGEX.match(request)
        if match is not None:
            return request

        search_request = search(AO3_SEARCH_QUERY % request, num=1, stop=1)
        try:
            return next(search_request)
        except StopIteration:
            # We didn't find anything so return None.
            return

    def generate_response(self, link):
        assert link is not None
        return Story(link)

    def get_story(self, query):
        return Story(self.find_link(query))


try:
    from functools import lru_cache
except ImportError:
    def lru_cache(*args, **kwargs):
        def _decorator(fnc):
            return fnc
        print("Warning: Python is too old for this cache variant.")
        return _decorator


@lru_cache(maxsize=10000)
def Story(link):
    return AO3Story(link)


class AO3Story(site.Story):

    def __init__(self, url):
        self.url = url
        self.raw_stats = []

        self.stats = ""
        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""

        self.parse_html()

    def get_real_url(self):
        return "http://archiveofourown.org/works/%s" % AO3_LINK_REGEX.match(self.url).groupdict()["sid"]

    def get_value_from_tree(self, xpath, sep=""):
        return sep.join(self.tree.xpath(xpath)).strip()

    def parse_html(self):
        result = get(self.get_real_url())
        self.tree = html.fromstring(result.text)

        self.summary = self.get_value_from_tree(AO3_SUMMARY_FINDER)
        self.title = self.get_value_from_tree(AO3_TITLE)
        self.author = self.get_value_from_tree(AO3_AUTHOR_NAME)
        self.authorlink = self.get_value_from_tree(AO3_AUTHOR_URL)
        self.stats = self.get_value_from_tree(AO3_META_PARTS, " ")
