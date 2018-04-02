# -*- encoding: utf-8 -*-
import re
from .parser import RequestParser


class Request(object):
    """
    This class stores a comment
    """

    # Allow to modify the behaviour of the comments
    # by adding a special function into the system
    #
    # Currently the following markers are supported:
    # ffnbot!ignore              Ignore the comment entirely
    # ffnbot!distinct:false      Don't make sure that we get distinct requests
    # ffnbot!directlinks         Also extract story requests from direct links
    CONTEXT_MARKER_REGEX = re.compile(r"ffnbot!([A-Za-z]+)")

    def __init__(self, request, markers=None):
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
        return self.request

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

    def get_parsers(self):
        """
        Returns all parsers that can be used with this parser.
        :returns: A generator that yields all supported parsers
        """
        yield from RequestParser.get_parsers()

    def parse(self):
        """
        Parses the request using the parsers defined in the global parser list.
        """
        self.markers.update(self.parse_markers())

        for parser in self.get_parsers():
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
                    continue
                yield marker.split(':', 2)


