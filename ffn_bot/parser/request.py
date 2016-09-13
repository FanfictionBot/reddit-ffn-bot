# -*- encoding: utf-8 -*-
import re
from .parser import RequestParser


class Request(object):
    """
    This class stores a comment
    """

    CONTEXT_MARKER_REGEX = re.compile(r"ffnbot!([^ ]+)")

    def __init__(self, reddit, request, markers=None):
        self.reddit = reddit
        self.request = request
        self.parsed = False

        self.markers = markers
        if self.markers is None:
            self.markers = {}

        self.stories = []

    @property
    def content(self):
        """
        Returns the actual content of the submission.
        :return: A string containing the content of the submission.
        """
        return ""

    @property
    def parent(self):
        """
        Returns the parent requests of this request.
        :return: A Request-object for every request that has a parent or None for an object without a parent.
        """
        return None

    @property
    def root(self):
        """
        Return the root-request of this tree.
        :return: The root-request of this tree.
        """
        return self

    @property
    def sender(self):
        """
        The sender that generated the request.
        :return: A string with the username that generated the request.
        """
        return '<Unknown>'

    def parse(self):
        """
        Parses the request using the parsers defined in the global parser list.
        """
        self.markers.update(self.parse_markers())

        for parser in RequestParser.PARSERS:
            # Check if this parser applies to this request.
            if not parser.is_active(self):
                continue

            # Execute the parser if it applies.
            if not parser.parse(self):
                # And break if the parser tells us to stop.
                break

    def parse_markers(self):
        """
        This function parses the markers inside the bot.
        :param comment: The comment to parse.
        :return: Yields a tuple for each entry inside the context marker.
        """
        for entry in self.CONTEXT_MARKER_REGEX.findall(self.content):
            for marker in entry.split(","):
                if ":" not in marker:
                    yield (marker, None)
                yield marker.split(':', 2)


class Submission(Request):
    """
    Represents a praw.objects.Submission-object.
    """

    @property
    def content(self):
        return self.request.selftext


class Comment(Request):
    """
    Represents a praw.objects.Comment-object
    """

    @property
    def content(self):
        return self.request.body

    @property
    def parent(self):
        if self.request.is_root:
            return self.root
        return Comment(self.reddit, self.reddit.get_info(thing_id = self.request.parent_id))

    @property
    def root(self):
        return Submission(self.reddit, self.request.submission)