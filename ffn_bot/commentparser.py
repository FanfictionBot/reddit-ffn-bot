"""
This file handles the comment parsing.
"""
import re
import itertools
from ffn_bot.fetchers import SITES, get_sites


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


def parse_context_markers(comment_body):
    """
    Changes the context of the story subsystem.
    """
    # The power of generators, harnessed in this
    # oneliner.
    return set(
        s.lower() for s in itertools.chain.from_iterable(
            v.split(",") for v in CONTEXT_MARKER_REGEX.findall(comment_body)))


def get_direct_links(string, markers):
    direct_links = []
    for site in SITES:
        direct_links.append(site.extract_direct_links(string, markers))
    # Flatten the story-list
    return itertools.chain.from_iterable(direct_links)


def formulate_reply(comment_body, markers=None, additions=()):
    """Creates the reply for the given comment."""
    if markers is None:
        # Parse the context markers as some may be required here
        markers = parse_context_markers(comment_body)

    # Ignore this message if we hit this marker
    if "ignore" in markers:
        return None

    requests = {}
    # Just parse normally of nothing other turns up.
    for site in SITES:
        tofind = re.findall(site.regex, comment_body)
        requests[site.name] = tofind

    direct_links = additions
    if "directlinks" in markers:
        direct_links = itertools.chain(
            direct_links, get_direct_links(comment_body, markers))

    return parse_comment_requests(requests, markers, direct_links)


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
    return "".join(str(result) for result in results if result)


def _parse_comment_requests(requests, context):
    sites = get_sites()
    for site, queries in requests.items():
        if len(queries) > 0:
            print("Requests for '%s': %r" % (site, queries))
        for query in queries:
            for comment in sites[site].from_requests(query.split(";"),
                                                     context):
                if comment is None:
                    continue
                yield comment
