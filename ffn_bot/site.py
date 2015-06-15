import re


WHITESPACE = re.compile("(^|[ ]+(?!\Z))")


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

    def from_requests(self, requests):
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

    def __init__(self):
        pass

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
        self.stats = re.sub('(\w+:)', '\n\n*' + r"\1" + '*', self.stats)
        self.stats = re.sub('((\w|[/>,\.\-\(])+)', '^' + r'\1', self.stats)
        self.stats = re.sub('([\n]+)', '\n', self.stats)
        self.stats = re.sub('([\n]+)', ' ^**|** ', self.stats)
        self.stats = '>' + self.stats

        # Hardcoded because I don't know regex well yet.
        self.stats = self.stats.replace("^-  ^**|** ", " ^**|** ")
        self.stats = self.stats.replace("  ^**|**   ^**|**", "")
        self.stats = self.stats.replace("^**|**    ^**|**", " ^**|** ")
        self.stats = self.stats.replace("> ^**|**", "> ")
        self.stats = self.stats.replace("^(Work ^in ^progress)", "^(Work In Progress)")
