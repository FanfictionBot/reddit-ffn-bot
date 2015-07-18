"""
This file handles the comment parsing.
"""
import re
import itertools
from ffn_bot import site
from ffn_bot.fetchers import SITES, get_sites


STORIES_PER_REPLY = 10
MAX_STORIES_PER_POST = 30


# Allow to modify the behaviour of the comments
# by adding a special function into the system
#
# Currently the following markers are supported:
# ffnbot!ignore              Ignore the comment entirely
# ffnbot!noreformat          Fix FFN formatting by not reformatting.
# ffnbot!nodistinct          Don't make sure that we get distinct requests
# ffnbot!directlinks         Also extract story requests from direct links
# ffnbot!submissionlink      Direct-Links just for the submission-url
CONTEXT_MARKER_REGEX = re.compile(r"ffnbot!([^ ]+)")


class StoryLimitExceeded(Exception):
    pass


def parse_context_markers(comment_body):
    """
    Changes the context of the story subsystem.
    """
    # The power of generators, harnessed in this
    # oneliner
    return set(
        s.lower() for s in itertools.chain.from_iterable(
            v.split(",") for v in CONTEXT_MARKER_REGEX.findall(comment_body)))


def get_direct_links(string, markers):
    for site in SITES:
        yield from site.extract_direct_links(string, markers)


def formulate_reply(comment_body, markers=None, additions=()):
    """Creates the reply for the given comment."""
    if markers is None:
        # Parse the context markers as some may be required here
        markers = parse_context_markers(comment_body)

    # Ignore this message if we hit this marker
    if "ignore" in markers:
        return

    requests = []
    # Just parse normally of nothing other turns up.
    for site in SITES:
        tofind = site.regex.findall(comment_body)

        # Split the request list using semicolons.
        request_list = []
        for item in tofind:
            request_list.extend(item.split(";"))

        # Ensure we don't have empty request lists.
        if not request_list:
            continue

        requests.append((site, request_list))

    direct_links = additions
    if "directlinks" in markers:
        direct_links = itertools.chain(
            direct_links, get_direct_links(comment_body, markers))

    yield from parse_comment_requests(requests, markers, direct_links)


def parse_comment_requests(requests, context, additions):
    """
    Executes the queries and return the
    generated story strings as a single string
    """
    # Merge the story-list
    results = itertools.chain(
        _parse_comment_requests(requests, context), additions)

    if "nodistinct" not in context:
        results = set(results)

    if len(tuple(filter(
            lambda x:isinstance(x, site.Story), results
    ))) > MAX_STORIES_PER_POST:
        raise StoryLimitExceeded("Maximum exceeded.")

    cur_part = []
    for part in results:
        if not part:
            continue

        if len(cur_part) == STORIES_PER_REPLY:
            yield "".join(str(p) for p in cur_part)
            cur_part = []

        cur_part.append(part)
    yield "".join(str(p) for p in cur_part)


def _parse_comment_requests(requests, context):
    for site, queries in requests:
        print("Requests for '%s': %r" % (site.name, queries))
        for comment in site.from_requests(queries, context):
            if comment is None:
                continue
            yield comment
