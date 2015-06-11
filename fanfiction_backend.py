from lxml import html
from lxml import etree
import requests
import urllib.request


class Story:

    def __init__(self, url):
        self.url = url
        self.raw_data = []

        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""
        self.data = ""
        
        self.parse_html(url)
        self.encode()

    def parse_html(self, url):
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

# # DEBUG
# x = Story('https://www.fanfiction.net/s/8303194/1/Magics-of-the-Arcane')
# print(x.authorlink)
# print(x.title)
# print(x.author)
# print(x.summary)
# print(x.data)
