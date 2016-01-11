import re
from ffn_bot import bot_tools
from ffn_bot import site
from ffn_bot.cache import get_default_cache
from ffn_bot.metaparse import Metaparser, parser

from random import randint
from lxml import html

__all__ = ["FanfictionNetSite", "FictionPressSite"]

LINK_REGEX = "http(s?)://((www|m)\\.)?%s/s/(?P<sid>\\d+).*"
ID_LINK = "https://www.{0}/s/%s"

FFN_GENRES = [
    "Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
    "Friendship", "General", "Horror", "Humor", "Hurt-Comfort", "Mystery",
    "Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual", "Supernatural",
    "Suspense", "Tragedy", "Western"
]

DOMAIN_TO_ARCHIVE_NAME = {
    "fanfiction.net": "fanfiction.net",
    "fictionpress.com": "FictionPress"
}


class FanfictionParser(Metaparser):
    CATEGORY_TYPE = "Category"

    @staticmethod
    def get_story_information(tree):
        if tree.xpath('//*[@id="profile_top"]/span[1]/img'):
            return "".join(
                tree.xpath('//*[@id="profile_top"]/span[4]//text()'))
        else:
            return "".join(
                tree.xpath('//*[@id="profile_top"]/span[3]//text()'))

    @parser
    @classmethod
    def parse_category(cls, id, tree):
        return (
            cls.CATEGORY_TYPE, tree.xpath(
                '//*[@id="pre_story_links"]/span/a[last()]/text()')[0]
        )

    @parser
    @classmethod
    def parse_metadata_simple(cls, id, tree):
        story_info = cls.get_story_information(tree)
        for part in re.split(r"\s+-\s+", story_info):
            subparts = re.split(r":\s+", part)
            if len(subparts) == 2:
                yield subparts

    @parser
    @classmethod
    def parse_unnamed_parts(cls, id, tree):
        n_unnamed = 0
        story_info = cls.get_story_information(tree)
        for part in re.split(r"\s+-\s+", story_info):
            subparts = re.split(r":\s+", part)
            if len(subparts) == 2:
                continue

            subpart = subparts[0]
            if n_unnamed == 0:
                yield "Language", subpart
            elif (
                n_unnamed == 1 and sum(
                    (g.strip() in FFN_GENRES)
                    for g in subpart.split("/"))):
                yield "Genre", subpart
            else:
                yield "Characters", subpart
            n_unnamed += 1

    @classmethod
    def create_implementation(cls, category):
        return type(cls).__new__(
            type(cls), "<FFNParser>", (cls,),
            {"CATEGORY_TYPE": category})


class FanfictionBaseSite(site.Site):
    # All regexps are automatically case insensitive for sites.

    def __init__(self, site, command, name=None, category="Category"):
        super(FanfictionBaseSite, self).__init__(command, name)
        self.site = site
        self.link_regex = re.compile(
            LINK_REGEX % self.site.replace(".", "\\."), re.IGNORECASE)
        self.id_link = ID_LINK.format(self.site)
        self.parser = FanfictionParser.create_implementation(category)

    def from_requests(self, requests, context):
        # I'd love to use 'yield from'
        for request in requests:
            yield self.process(request, context)

    def process(self, request, context):
        try:
            link = self.find_link(request, context)
        except (StopIteration, Exception):
            bot_tools.print_exception()
            return None

        if link is None:
            return None

        try:
            return self.generate_response(link, context)
        except Exception:
            bot_tools.print_exception()
            return None

    def generate_response(self, link, context):
        return Story(link, self.site, context, self.parser)

    def find_link(self, fic_name, context):
        # Prevent users from crashing program eith bad link names.
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

        return get_default_cache().search(
            fic_name, "http://www." + self.site + "/s/"
        )

    def extract_direct_links(self, body, context):
        return (
            (
                match.start(0),
                self.generate_response(self.id_link % match.group(4), context)
            )
            for match in self.link_regex.finditer(body)
        )


class Story(site.Story):

    def __init__(self, url, site, context, parser):
        super(Story, self).__init__(context)
        self.url = url
        self.site = site
        self.stats = ""

        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""

        self.parser = parser

    def get_url(self):
        return "http://www.%s/s/%s/1/" % (
            self.site,
            re.match(LINK_REGEX % self.site, self.url).groupdict()["sid"])

    def parse_html(self):
        page = get_default_cache().get_page(
            self.get_url(),
            throttle=randint(1000, 4000) / 1000)
        tree = html.fromstring(page)

        self.title = (tree.xpath('//*[@id="profile_top"]/b/text()'))
        if not len(self.title):
            raise site.StoryDoesNotExist
        self.title = self.title[0]

        self.summary = (tree.xpath('//*[@id="profile_top"]/div/text()'))[0
                                                                         ]
        self.author += (tree.xpath('//*[@id="profile_top"]/a[1]/text()'))[
            0
        ]
        self.authorlink = 'https://www.' + self.site + tree.xpath(
            '//*[@id="profile_top"]/a[1]/@href')[0]
        self.image = tree.xpath('//*[@id="profile_top"]/span[1]/img')
        self.tree = tree
        self.stats = self.parser(None, tree)

    def get_site(self):
        link = "http://www." + self.site + "/"
        return (DOMAIN_TO_ARCHIVE_NAME[self.site], link)

    def get_download(self):
        if "fictionpress" in self.url:
            return "http://ficsave.com/?story_url={0}&format=epub&auto_download=yes".format(self.url)
        else:
            return "http://www.p0ody-files.com/ff_to_ebook/mobile/makeEpub.php?id={0}".format(
                re.findall(r'\d+', self.url)[0])


class FanfictionNetSite(FanfictionBaseSite):

    def __init__(self, command="linkffn", name=None):
        super(FanfictionNetSite, self).__init__(
            "fanfiction.net", "linkffn", name, "Fandom")


class FictionPressSite(FanfictionBaseSite):

    def __init__(self, command="linkfp", name=None):
        super(FictionPressSite, self).__init__(
            "fictionpress.com", "linkfp", name, "Category")
