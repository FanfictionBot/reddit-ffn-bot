import re
from collections import OrderedDict
import logging

from ffn_bot import reddit_markdown

WHITESPACE = re.compile("(|[ ]+(?!\Z))")


class StoryDoesNotExist(Exception):
    pass


class Site(object):
    """
    Base-Class for a supported fanfiction archive.
    """

    def __init__(self, fname, name=None):
        """
        Sets the state of the site.

        :param regex:  The regular expression that will be used
                       to find the requests.
        :param name:   The internal name of the site.
                       (Defaults to the class name.)
        """
        if name is None:
            # Automatically assign a name for the site.
            name = self.__class__.__module__ + "." + self.__class__.__name__
        self.regex = re.compile(
            re.escape(fname) + r"\((.*?)\)",
            re.IGNORECASE
        )
        self.name = name

    def extract_direct_links(self, body, context):
        """
        Extracts all direct links

        It is the responsibility of the site-class to
        make sure, that there will be no repeated requests.

        :param body:  The comment body.
        :param context:  The comment context.
        :returns: An iterable of story objects.
        """
        return ()

    def from_requests(self, requests, context):
        """
        Returns an iterable of story objects that are assiciated with this
        request.
        :param request:  The list of request that have been sent.
        :returns: An iterable of Story objects.
        """
        return ()


class Story(object):
    """
    Represents a single story.
    """

    def __init__(self, context=None):
        self.context = set() if context is None else context
        self._loaded = False

    def get_title(self):
        """Returns the title of the story"""
        return self.title

    def get_site(self):
        """Return the name of the site. (None means unknown)"""
        return None

    def get_download(self):
        """Return the EPUB and MOBI download link for a fic."""
        return None

    def get_summary(self):
        """Returns the summary of the story."""
        return self.summary

    def get_author(self):
        """Returns the author of the story."""
        return self.author

    def get_author_link(self):
        """Returns the link to the userpage of the author."""
        return self.authorlink

    def get_url(self):
        """Returns the link to the story."""
        return self.url

    def get_stats(self):
        """Returns the stats to the story."""
        return self.stats

    def __str__(self):
        """Generates the response string."""
        try:
            self.load()
        except Exception as e:
            logging.error("(STORY) Could not load story!")
            logging.error(e)
            return("")
        result = ["\n\n"]
        result.append(
            reddit_markdown.link(
                reddit_markdown.bold(
                    reddit_markdown.italics(
                        reddit_markdown.escape(self.get_title()))),
                reddit_markdown.encode_url(self.get_url())) + " by " +
            reddit_markdown.link(
                reddit_markdown.italics(
                    reddit_markdown.escape(self.get_author())),
                reddit_markdown.encode_url(self.get_author_link())))
        result.append("\n\n")
        # result.append("\n\n[***%s***](%s) by [*%s*](%s)" %
        #     self.get_title(), self.get_url(),
        #     self.get_author(), self.get_author_link()
        # ))

        result.append("\n\n")
        result.extend(
            reddit_markdown.quote(
                reddit_markdown.escape(self.get_summary())).split("\n"))
        result.append("")
        result.append(reddit_markdown.exponentiate(self.format_stats()))
        # result.append("[" + str(id(self)) + "]: " + self._lnk)
        for name, link in self._lnk:
            result.append("[%s:%s]: %s" % (str(id(self)), name, link))

        result.append("\n\n" + reddit_markdown.linebreak + "\n\n")

        return "\n".join(result)

    def format_stats(self):
        stats = OrderedDict()
        site = self.get_site()
        self._lnk = []
        if site is not None:
            _site = iter(site)
            site = "[" + next(_site) + "][" + str(id(self)) + ":site]"
            self._lnk.append(("site", next(_site)))
            stats["Site"] = site

        for k, v in self.get_stats().items():
            stats[self.super_escape(k)] = self.super_escape(v)

        res = []
        for key, value in stats.items():
            res.append(reddit_markdown.italics(key) + ": " + value)

        download = self.get_download()
        if download is not None:
            epub = download[0]
            mobi = download[1]
            res.append(
                "*Download*: [EPUB][{0}:epub] or [MOBI][{1}:mobi]".format(str(id(self)), str(id(self))))
            self._lnk.append(("epub", epub))
            self._lnk.append(("mobi", mobi))
        return (" " + reddit_markdown.bold("|") + " ").join(res)

    @staticmethod
    def super_escape(string):
        for c in "([{":
            string = string.replace(c, "<")
        for c in ")]}":
            string = string.replace(c, ">")
        return string

    def __hash__(self):
        # We will use the URL for a hash.
        try:
            return hash(self.get_url())
        except:
            return 0

    def __eq__(self, other):
        if not isinstance(other, Story):
            return False
        return other.get_url() == self.get_url()

    def load(self):
        if not self._loaded:
            self.parse_html()
        self._loaded = True

    def parse_html(self):
        pass
