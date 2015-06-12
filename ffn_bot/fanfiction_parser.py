import time
import logging
import requests
from random import randint
from google import search
from lxml import html


def ffn_make_from_requests(fic_requests):
    found_ffn = ffn_comment_maker(ffn_link_finder(fic_requests))
    return found_ffn


def safe_int(request):
    try:
        return int(request)
    except ValueError:
        return None


def ffn_link_finder(fic_names):
    for fic_name in fic_names:
        # Allow just to post the ID of the fanfiction.
        sid = safe_int(fic_name)
        if sid is not None:
            yield "https://www.fanfiction.net/s/%d/1/" % sid
            continue

        # Obfuscation.
        time.sleep(randint(1, 3))
        sleep_milliseconds = randint(500, 3000)
        time.sleep(sleep_milliseconds / 1000)

        search_request = 'site:fanfiction.net/s/ {0}'.format(fic_name)
        print("SEARCHING: ", search_request)

        search_results = search(search_request, num=1, stop=1)
        link_found = next(search_results)
        print("FOUND: " + link_found)
        yield link_found


def ffn_comment_maker(links):
    comment = []
    for link in links:
        # preparation for caching of known stories, should cache last X stories
        # and be able to search cached by name or link or id
        current = Story(link)
        comment.append('{0}\n&nbsp;\n\n'.format(ffn_description_maker(current)))
    return "".join(comment)


def ffn_description_maker(current):
    decoded_title = current.title.decode('ascii', errors='replace')
    decoded_author = current.author.decode('ascii', errors='replace')
    decoded_summary = current.summary.decode('ascii', errors='replace')
    decoded_data = current.data.decode('ascii', errors='replace')
    print("Making a description for " + decoded_title)

    # More pythonic string formatting.
    header = '[***{0}***]({1}) by [*{2}*]({3})'.format(decoded_title,
                                                       current.url, decoded_author, current.authorlink)

    formatted_description = '{0}\n\n>{1}\n\n>{2}\n\n'.format(
        header, decoded_summary, decoded_data)
    return formatted_description


class _Story:

    def __init__(self, url):
        self.url = url
        self.raw_data = []

        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""
        self.data = ""

        self.parse_html()
        self.encode()

    def parse_html(self):
        page = requests.get(self.url)
        tree = html.fromstring(page.text)

        self.title = (tree.xpath('//*[@id="profile_top"]/b/text()'))[0]
        self.summary = (tree.xpath('//*[@id="profile_top"]/div/text()'))[0]
        self.author += (tree.xpath('//*[@id="profile_top"]/a[1]/text()'))[0]
        self.authorlink = 'https://www.fanfiction.net' + \
                          tree.xpath('//*[@id="profile_top"]/a[1]/@href')[0]

        # Getting the metadata was a bit more tedious.
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/a[1]/text()'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/text()[2]'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/a[2]/text()'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/text()[3]'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/span[1]/text()'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/text()[4]/text()'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/span[2]/text()'))
        self.raw_data += (tree.xpath('//*[@id="profile_top"]/span[4]/text()[5]'))

    def encode(self):
        self.title = self.title.encode('ascii', errors='replace')
        self.author = self.author.encode('ascii', errors='replace')
        self.summary = self.summary.encode('ascii', errors='replace')
        self.data = self.data.encode('ascii', errors='replace')
        for string in self.raw_data:
            self.data += string.encode('ascii', errors='replace')

# Implement a cached version if the lru_cache is
# implemented in this version of python.
try:
    from functools import lru_cache
except ImportError:
    print("Python version too old for caching.")
    Story = _Story
else:
    # We will use a simple lru_cache for now.
    @lru_cache(maxsize=10000)
    def Story(url):
        return _Story(url)

# # DEBUG
# x = Story('https://www.fanfiction.net/s/8303194/1/Magics-of-the-Arcane')
# print(x.authorlink)
# print(x.title)
# print(x.author)
# print(x.summary)
# print(x.data)
