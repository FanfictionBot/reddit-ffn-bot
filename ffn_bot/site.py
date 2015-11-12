import re
from collections import OrderedDict

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
        self._disabled = False

    def _update_settings(self, settings):
        """
        Update the internal site settings.
        """
        self._disabled = settings.get("disabled", False)
        self.update_settings(settings)

    def update_settings(self, settings):
        """
        Update the settings of the actual site implementation.
        """
        pass

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
        """Return the EPUB download link from FicSave"""
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

    def __hash__(self):
        # We will use the URL for a hash.
        return hash(self.get_url())

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


class Group(object):
    """
    Represents a group of stories.
    The stories are queried lazily.
    """

    def __init__(self, header=""):
        self.header = header
        self.stories = []

    def add(self, story):
        self.stories.append(story)

    def __rsub__(self, other):
        if isinstance(other, (set, frozenset)):
            return other - set(self.stories)
        raise NotImplemented

    def __contains__(self, obj):
        return obj in self.stories

    def __getitem__(self, item):
        if isinstance(item, slice):
            result = Group(self.header)
            result.stories = self.stories[item]
            return result
        return self.stories[item]

    def __len__(self):
        return len(self.stories)

