import re
import sys
import time
import logging
import requests

from ffn_bot import bot_tools
from ffn_bot import site
from random import randint
from google import search
from lxml import html

__all__ = ["FanfictionNetSite", "FictionPressSite"]

LINK_REGEX = "http(s?)://((www|m)\\.)?%s/s/(\\d+)/.*"
ID_LINK = "https://www.{0}/s/%s"


class FanfictionBaseSite(site.Site):
    # All regexps are automatically case insensitive for sites.

    def __init__(self, site, command, name=None):
        super(FanfictionBaseSite, self).__init__(command + r"\((.*?)\)", name)
        self.site = site
        self.link_regex = re.compile(LINK_REGEX % self.site.replace(".", "\\."), re.IGNORECASE)
        self.id_link = ID_LINK.format(self.site)

    @staticmethod
    def safe_int(value):
        try:
            return int(value)
        except ValueError:
            return None

    def from_requests(self, requests):
        # I'd love to use 'yield from'
        for request in requests:
            yield self.process(request)

    def process(self, request):
        try:
            link = self.find_link(request)
        except (StopIteration, Exception) as e:
            bot_tools.print_exception()
            return ""
        try:
            return str(Story(link, self.site))
        except Exception as e:
            bot_tools.print_exception()
            return ""

    def find_link(self, fic_name):
        # Prevent users from crashing program with bad link names.
        fic_name = fic_name.encode('ascii', errors='replace')
        fic_name = fic_name.decode('ascii', errors='replace')

        # Allow just to post the ID of the fanfiction.
        sid = FanfictionNetSite.safe_int(fic_name)
        if sid is not None:
            return self.id_link % sid

        # Yield links directly without googling.
        match = self.link_regex.match(fic_name)
        if match is not None:
            return fic_name

        # Obfuscation.
        time.sleep(randint(1, 3))
        sleep_milliseconds = randint(500, 3000)
        time.sleep(sleep_milliseconds / 1000)

        search_request = 'site:www.{1}/s/ {0}'.format(fic_name,self.site)
        print("SEARCHING: ", search_request)
        search_results = search(search_request, num=1, stop=1)
        link_found = next(search_results)
        print("FOUND: " + link_found)
        return link_found


class _Story(site.Story):

    def __init__(self, url, site):
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

    def parse_html(self):
        page = requests.get(self.url)
        tree = html.fromstring(page.text)

        self.title = (tree.xpath('//*[@id="profile_top"]/b/text()'))[0]
        self.summary = (tree.xpath('//*[@id="profile_top"]/div/text()'))[0]
        self.author += (tree.xpath('//*[@id="profile_top"]/a[1]/text()'))[0]
        self.authorlink = 'https://www.' + self.site + \
            tree.xpath('//*[@id="profile_top"]/a[1]/@href')[0]
        self.image = tree.xpath('//*[@id="profile_top"]/span[1]/img')

        # XPath changes depending on the presence of an image

        if len(self.image) is not 0:
            self.raw_stats = tree.xpath('//*[@id="profile_top"]/span[4]//text()')
        else:
            self.raw_stats = tree.xpath('//*[@id="profile_top"]/span[3]//text()')

    def encode(self):
        self.title = self.title.encode('ascii', errors='replace')
        self.author = self.author.encode('ascii', errors='replace')
        self.summary = self.summary.encode('ascii', errors='replace')
        self.stats = self.stats.encode('ascii', errors='replace')
        for string in self.raw_stats:
            self.stats += string.encode('ascii', errors='replace')

    def decode(self):
        _decode = lambda s: s.decode('ascii', errors='replace')
        self.title = _decode(self.title)
        self.author = _decode(self.author)
        self.summary = _decode(self.summary)
        self.stats = _decode(self.stats)

    # def __str__(self):
    #    decoded_title = self.title.decode('ascii', errors='replace')
    #    decoded_author = self.author.decode('ascii', errors='replace')
    #
    #    decoded_summary = self.summary.decode('ascii', errors='replace')
    #    decoded_stats = self.stats.decode('ascii', errors='replace')
    #    formatted_stats = decoded_stats.replace(' ', ' ').replace(' ', ' ').replace( ' ', ' ^').replace('Rated:', '^Rated:') 
    #    formatted_stats = formatted_stats[:-1]
    #    # print("Making a description for " + decoded_title) # More pythonic string formatting.
    #    header = '[***{0}***]({1}) by [*{2}*]({3})'.format(
    #        decoded_title,
    #        self.url,
    #        decoded_author,
    #        self.authorlink
    #    )
    #
    #    formatted_description = '{0}\n\n>{1}\n\n>{2}\n\n'.format(
    #        header,
    #        decoded_summary,
    #        formatted_stats
    #    )
    #    return formatted_description


class FanfictionNetSite(FanfictionBaseSite):
    def __init__(self, command="linkffn", name=None):
        super(FanfictionNetSite, self).__init__("fanfiction.net", "linkffn", name)


class FictionPressSite(FanfictionBaseSite):
    def __init__(self, command="linkfp", name=None):
        super(FictionPressSite, self).__init__("fictionpress.com", "linkfp", name)


try:
    from functools import lru_cache
except ImportError:
    print("Python version too old for caching.")
    Story = _Story
else:
    # We will use a simple lru_cache for now.
    @lru_cache(maxsize=10000)
    def Story(url, site):
        return _Story(url, site)

# # DEBUG
# x = Story('https://www.fanfiction.net/s/11096853/1/She-Chose-Me')  # No self.image
# print(str(x))
# print(x.authorlink)
# print(x.title)
# print(x.author)
# print(x.summary)
# print(x.stats)
