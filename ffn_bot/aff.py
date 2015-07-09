import re

from lxml import html
from lxml.cssselect import CSSSelector

from ffn_bot.cache import default_cache
from ffn_bot.bot_tools import safe_int
from ffn_bot.site import Site
from ffn_bot import site

# This regexes will be tried to generate a response
AFF_MATCH_REGEX = (
    # We really need the link regex to work
    # as we are unable to google for the story.
    # Format:
    # http://<archive>.adult-fanfiction.org/story.php?no=<id>
    re.compile(
        r"http(?:s)?://([^.]+)\.adult-fanfiction\.org/story\.php\?no=(\d+)",
        re.IGNORECASE
    ),

    # We need the id to be passed like this:
    # <Archive>:<ID>
    re.compile(
        "([^:]+):(\d+)",
        re.IGNORECASE
    ),
)

AFF_LINK_REGEX = AFF_MATCH_REGEX[0]

# As we don't have a general archive, we will need also the archive
# Subdomain provided.
AFF_LINK_BY_ID = "http://{0}.adult-fanfiction.org/story.php?no={1}"

# I have no idea if it is really neccessary.
AFF_BYPASS_COOKIE = (
    "HasVisited=bypass page next time; path=/; "
    "domain={0}.adult-fanfiction.org"
)

AFF_TITLE_XPATH = "//html/head/title/text()"
AFF_AUTHOR_NAME = "//tr[5]/td[2]//a/text()"
AFF_AUTHOR_URL = "//tr[5]/td[2]//a/@href"

# Since we don't have an explicit summary we will just access
# the metadata ourselves.
AFF_DEFAULT_SUMMARY = ""

# Generate the metadata with this values
AFF_GENERATED_META = (
    ("Archive", (
        lambda tree, archive, id: archive
    )),
    ("Category", (
        lambda tree, archive, id: " > ".join(
            x.strip()
            for x in tree.xpath("//tr[5]//td[1]//a/text()")
            if x.strip() != "Next chapter>"
        ).replace(" - ", "-")
    )),
    ("Chapters", (
        lambda tree, archive, id: len(
            tree.xpath("//select[@name='chapnav']/option")
        )
    )),
    ("Hits", (
        lambda tree, archive, id: (
            tree.xpath("//tr[5]/td[3]/text()")[0].strip()[len("Hits: "):]
        )
    )),
    ("ID", (
        lambda tree, archive, id: id
    ))
)

class AdultFanfiction(Site):
    """
    Implementation of adult fanfiction
    """

    def __init__(self):
        super(AdultFanfiction, self).__init__(r"linkaf\([^)]+)")

    def from_requests(self, requests, context):
        for request in requests:
            yield self.process(request, context)

    def process(self, request, context):
        for regex in AFF_MATCH_REGEX:
            match = regex.match(request)
            if match is not None:
                return self.get_story_by_id(context, *match.groups())

    def get_story_by_id(self, context, archive, id):
        return Story(context, archive, id)

    def extract_direct_links(self, body, context):
        return (
            self.get_story_by_id(context, *match)
            for match in AFF_LINK_REGEX.findall(body)
        )

    def get_story(self, query):
        return self.process(query, set())


class Story(site.Story):
    """
    Implementation of a story
    """

    def __init__(self, context, archive, id):
        super(Story, self).__init__(context)
        self.archive = archive
        self.id = id
        self.parse_html()

    def parse_html(self):
        tree = html.fromstring(default_cache.get_page(
            self.get_url(),

            # Got this header from the ficsave codebase
            headers = {
                "Cookie": AFF_BYPASS_COOKIE
            },
            # Do not even try to follow to the adult form url.
            allow_redirects=False
        ))

        # We will generate the stats ourselves.
        self.stats = " - ".join((
            (title + ": " + str(result(
                tree, self.archive, self.id
            )))
            for title, result in AFF_GENERATED_META
        ))

        self.title = tree.xpath(AFF_TITLE_XPATH)[0].strip()[len("Story: "):]
        self.author = tree.xpath(AFF_AUTHOR_NAME)[0].strip()
        self.authorlink = tree.xpath(AFF_AUTHOR_URL)[0]

    def get_summary(self):
        return AFF_DEFAULT_SUMMARY

    def get_url(self):
        return AFF_LINK_BY_ID.format(self.archive, self.id)
