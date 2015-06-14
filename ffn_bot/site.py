import re


WHITESPACE = re.compile("(^|[ ]+(?!\Z))")


class Site(object):
    def __init__(self, regex, name=None):
        if name is None:
            # Automatically assign a name for the site.
            name = self.__class__.__module__ + "." + self.__class__.__name__
        self.regex = regex
        self.name = name

    def from_requests(self, requests):
        return ()


class Story(object):
    def __init__(self):
        pass
    def get_title(self):
        return self.title
    def get_summary(self):
        return self.summary
    def get_author(self):
        return self.author
    def get_author_link(self):
        return self.authorlink
    def get_url(self):
        return self.url
    def get_stats(self):
        return self.stats

    def __str__(self):
        result = []
        result.append("[***%s***](%s) by [*%s*](%s)" % (
            self.get_title(), self.get_url(),
            self.get_author(), self.get_author_link()
        ))

        result.append("")
        for line in self.get_summary().split("\n"):
            line = line.strip()
            result.append("> " + line)
        result.append("")
        print(self.get_stats())
        result.append(">" + WHITESPACE.sub(r"\g<0>^", self.get_stats()))
        return "\n".join(result)
