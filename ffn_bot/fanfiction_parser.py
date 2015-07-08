import re
import sys
import time
import logging
import requests
import itertools

from ffn_bot import bot_tools
from ffn_bot import site
from ffn_bot.cache import default_cache

from random import randint
from google import search
from lxml import html

__all__ = ["FanfictionNetSite", "FictionPressSite"]

LINK_REGEX = "http(s?)://((www|m)\\.)?%s/s/(?P<sid>\\d+).*"
ID_LINK = "https://www.{0}/s/%s"


class FanfictionBaseSite(site.Site):
    # All regexps are automatically case insensitive for sites.

    def __init__(self, site, command, name=None):
        super(FanfictionBaseSite, self).__init__(command + r"\((.*?)\)", name)
        self.site = site
        self.link_regex = re.compile(
            LINK_REGEX % self.site.replace(".", "\\."), re.IGNORECASE)
        self.id_link = ID_LINK.format(self.site)

    def from_requests(self, requests, context):
        # I'd love to use 'yield from'
        for request in requests:
            yield self.process(request, context)

    def process(self, request, context):
        try:
            link = self.find_link(request, context)
        except (StopIteration, Exception) as e:
            bot_tools.print_exception()
            return None

        if link is None:
            return None

        try:
            return Story(link, self.site, context)
        except Exception as e:
            bot_tools.print_exception()
            return None

    def find_link(self, fic_name, context):
        # Prevent users from crashing program with bad link names.
        fic_name = fic_name.encode('ascii', errors='replace')
        fic_name = fic_name.decode('ascii', errors='replace')

        # Allow just to post the ID of the fanfiction.
        sid = bot_tools.safe_int(fic_name)
        if sid is not None:
            return self.id_link % sid

        # Yield links directly without googling.
        match = self.link_regex.match(fic_name)
        if match is not None:
            return fic_name

        search_request = 'site:www.{1}/s/ {0}'.format(fic_name, self.site)
        return default_cache.search(search_request)


class Story(site.Story):

    def __init__(self, url, site, context):
        super(Story, self).__init__(context)
        self.url = url
        self.site = site
        self.raw_stats = []
        self.stats = ""

        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""

        self.parse_html()
        self.encode()
        self.decode()

    def get_url(self):
        return "http://www.%s/s/%s/1/" % (
            self.site,
            re.match(LINK_REGEX%self.site, self.url).groupdict()["sid"]
        )

    def parse_html(self):
        page = default_cache.get_page(self.get_url(), throttle=randint(1000,4000)/1000)
        tree = html.fromstring(page)

        self.title = (tree.xpath('//*[@id="profile_top"]/b/text()'))[0]
        self.summary = (tree.xpath('//*[@id="profile_top"]/div/text()'))[0]
        self.author += (tree.xpath('//*[@id="profile_top"]/a[1]/text()'))[0]
        self.authorlink = 'https://www.' + self.site + \
            tree.xpath('//*[@id="profile_top"]/a[1]/@href')[0]
        self.image = tree.xpath('//*[@id="profile_top"]/span[1]/img')

        self.raw_stats = []
        self.raw_stats.extend(
            tree.xpath('//*[@id="pre_story_links"]/span/a[last()]/text()'))
        self.raw_stats.extend(['\n'])

        # XPath changes depending on the presence of an image
        if len(self.image) is not 0:
            self.raw_stats.extend(tree.xpath('//*[@id="profile_top"]/span[4]//text()'))
        else:
            self.raw_stats.extend(tree.xpath('//*[@id="profile_top"]/span[3]//text()'))

    def encode(self):
        self.title = self.title.encode('ascii', errors='replace')
        self.author = self.author.encode('ascii', errors='replace')
        self.summary = self.summary.encode('ascii', errors='replace')
        self.stats = "".join(itertools.chain(
            (self.stats,), self.raw_stats)).encode('ascii', errors='replace')

    def decode(self):
        _decode = lambda s: s.decode('ascii', errors='replace')
        self.title = _decode(self.title)
        self.author = _decode(self.author)
        self.summary = _decode(self.summary)
        self.stats = _decode(self.stats)


class FanfictionNetSite(FanfictionBaseSite):

    def __init__(self, command="linkffn", name=None):
        super(FanfictionNetSite, self).__init__("fanfiction.net", "linkffn", name)


class FictionPressSite(FanfictionBaseSite):

    def __init__(self, command="linkfp", name=None):
        super(FictionPressSite, self).__init__("fictionpress.com", "linkfp", name)

# We don't need to cache the story objects anymore.

