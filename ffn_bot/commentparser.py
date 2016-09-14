"""
This file handles the comment parsing.
"""
import itertools
from ffn_bot import site

from ffn_bot.parser import Request


MAX_REPLY_LENGTH = 8000
MAX_STORIES_PER_POST = 30


class StoryLimitExceeded(Exception):
    pass


def formulate_reply(comment_body, markers=None, additions=()):
    """Creates the reply for the given comment."""
    if markers is None:
        markers = set()

    if isinstance(comment_body, str):
        request = Request(comment_body, {marker: None for marker in markers})
    else:
        request = comment_body
    request.parse()

    yield from parse_comment_requests(list(itertools.chain(request.stories, additions)))


def parse_comment_requests(results):
    """
    Executes the queries and return the
    generated story strings as a single string
    """
    if len(tuple(filter(
            lambda x: isinstance(x, site.Story), results
    ))) > MAX_STORIES_PER_POST:
        raise StoryLimitExceeded("Maximum exceeded.")

    cur_part = []
    length = 0
    for part in results:
        if not part:
            continue

        if length + len(str(part)) >= MAX_REPLY_LENGTH:
            yield "".join(str(p) for p in cur_part)
            cur_part = []
            length = 0

        cur_part.append(part)
        length += len(str(part))

    if len(cur_part) > 0:
        result = "".join(str(p) for p in cur_part)
        if result:
            yield result
