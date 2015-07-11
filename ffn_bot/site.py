import re
from ffn_bot import reddit_markdown


WHITESPACE = re.compile("(|[ ]+(?!\Z))")


class Site(object):

    """
    Base-Class for a supported fanfiction archive.
    """

    def __init__(self, regex, name=None):
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
        self.regex = regex
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
        Returns an iterable of story objects that are assiciated with this request.
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

    def get_title(self):
        """Returns the title of the story"""
        return self.title

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
        result = []
        result.append("\n\n[***%s***](%s) by [*%s*](%s)" % (
            self.get_title(), self.get_url(),
            self.get_author(), self.get_author_link()
        ))

        result.append("")
        for line in self.get_summary().split("\n"):
            line = line.strip()
            result.append("> " + line)
        result.append("")

        self.format_stats()
        result.append(self.stats)
        return "\n".join(result)

    def format_stats(self):
        # Allow the user to opt out of the reformatting
        if "noreformat" in self.context:
            return

        # Separate by lines.
        self.stats = re.sub('(\w+:)', '**|**' + reddit_markdown.italics(r"\1") + ' ', self.stats)

        # Fix the first word.
        self.stats = self.stats.replace('(**|**', '(')

        # Replace the "dashes" with spaces.
        self.stats = self.stats.replace('- **|**', '**|**')

        # Exponentiate.
        self.stats = reddit_markdown.exponentiate(self.stats)

    def __hash__(self):
        # We will use the URL for a hash.
        return hash(self.get_url())

    def __eq__(self, other):
        if not isinstance(other, Story):
            return False
        return other.get_url() == self.get_url()
