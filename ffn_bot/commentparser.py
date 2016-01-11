"""
This file handles the comment parsing.
"""
import re
import logging
import itertools

from ffn_bot import site
from ffn_bot.site import Group
from ffn_bot.config import get_settings
from ffn_bot.fetchers import SITES, get_sites

MAX_REPLY_LENGTH = 8000
MAX_STORIES_PER_POST = 30

MAX_GROUP_COUNT = 5
MAX_GROUP_LENGTH = 5

_UPDATED_SETTINGS = False

LOGGER = None
def get_logger():
    global LOGGER
    if not LOGGER:
        LOGGER = logging.getLogger("Parser")
    return LOGGER

def update_settings():
    global MAX_REPLY_LENGTH
    global MAX_STORIES_PER_POST
    global MAX_GROUP_COUNT
    global MAX_GROUP_LENGTH

    # Make sure we don't update the settings twice.
    global _UPDATED_SETTINGS
    if _UPDATED_SETTINGS:
        return
    _UPDATED_SETTINGS = True

    settings = get_settings()

    get_logger().info("Updating settings before parsing the first post.")
    MAX_REPLY_LENGTH = settings["parser"].get("reply-length", MAX_REPLY_LENGTH)
    MAX_STORIES_PER_POST = settings["parser"].get("stories-per-post", MAX_STORIES_PER_POST)
    MAX_GROUP_COUNT = settings["parser"].get("groups-per-post", MAX_GROUP_COUNT)
    MAX_GROUP_LENGTH = settings["parser"].get("stories-per-group", MAX_GROUP_LENGTH)

    get_logger().info("Initializing Fetchers before parsing the first post.")
    # Update the settings for the individual sites.
    site_settings = settings["parser"].get("sites", {})
    for site in SITES:
        site._update_settings(site_settings.get(site.name, {}))


# Allow to modify the behaviour of the comments
# by adding a special function into the system
#
# Currently the following markers are supported:
# ffnbot!ignore              Ignore the comment entirely
# ffnbot!nodistinct          Don't make sure that we get distinct requests
# ffnbot!directlinks         Also extract story requests from direct links
# ffnbot!submissionlink      Direct-Links just for the submission-url
CONTEXT_MARKER_REGEX = re.compile(r"ffnbot!([^ ]+)")


def _unique(iterable, key=lambda i:i):
    seen = set()
    iterable = tuple(iterable)

    for item in iterable:
        if not isinstance(item, Group):
            continue

        # Make sure stories inside groups will be purged
        # from non-group list.
        seen |= {key(story) for story in item}

    for item in iterable:
        if isinstance(item, Group):
            continue

        i = key(item)
        if i not in seen:
            seen.add(i)
            yield item


class StoryLimitExceeded(Exception):
    pass


class GroupLimitExceeded(Exception):
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


def parse_site_requests(comment_body, site):
    for request in site.regex.finditer(comment_body):
        cpos = request.start(1)
        queries = request.group(1)
        for query in re.split(r"(?<!\\);(?:\s*)", queries):
            yield cpos, query
            cpos += len(query)


def formulate_reply(comment_body, env, markers=None, additions=()):
    """Creates the reply for the given comment."""
    update_settings()

    if markers is None:
        # Parse the context markers as some may be required here
        markers = parse_context_markers(comment_body)

    # Ignore this message if we hit this marker
    if "ignore" in markers:
        return

    requests = []
    # Just parse normally of nothing other turns up.
    for site in SITES:
        request_list = list(parse_site_requests(comment_body, site))

        # Ensure we don't have empty request lists.
        if not request_list:
            continue

        requests.append((site, request_list))

    direct_links = additions
    if "directlinks" in markers:
        direct_links = itertools.chain(
            direct_links, get_direct_links(comment_body, markers))

    yield from parse_comment_requests(requests, env, markers, direct_links)


def create_story(part, env, markers):
    if isinstance(part, site.Story):
        try:
            part.load()
        except site.StoryDoesNotExist:
            get_logger().info("Found nonexistent story: " + part.get_url())
            return ""

    env.stats(part, markers)
    return env.to_string(part, markers)


def expel_stories(stories, env, markers):
    # Filter stories.
    stories = list(story for story in stories if isinstance(story, site.Story))
    if len(stories) > MAX_STORIES_PER_POST:
        raise StoryLimitExceeded("Too many stories.")
    # Just push out story objects.
    cur_part = []
    length = 0
    for part in stories:
        if not part:
            continue

        part = create_story(part, env, markers)

        if length + len(str(part)) >= MAX_REPLY_LENGTH:
            get_logger().info("Reached maximal reply length. Evicting.")
            yield "".join(str(p) for p in cur_part)
            cur_part = []
            length = 0

        cur_part.append(part)
        length += len(str(part))

    if len(cur_part) > 0:
        yield "".join(str(p) for p in cur_part)


def expel_groups(groups, env, markers):
    groups = list(group for group in groups if isinstance(group, Group))
    if len(groups) > MAX_GROUP_COUNT:
        raise GroupLimitExceeded("Max group count.")

    for group in groups:
        cur_part = []
        length = 0

        cur_part.append(group.header)
        cur_part.append("\n-----\n")
        length += len(group.header+7)

        # Try loading the next story in the group until we
        # exhausted our list.
        for i, story in enumerate(group):
            if i >= MAX_GROUP_LENGTH:
                break

            string = create_story(story, env, markers)
            if length+len(string) > MAX_REPLY_LENGTH:
                break
            cur_part.append(string)

        get_logger().info("Evicting group reply.")
        # Evict post.
        yield "".join(str(p) for p in cur_part)


def parse_comment_requests(requests, env, context, additions):
    """
    Executes the queries and return the
    generated story strings as a single string
    """
    # Get the stories.
    results = list(_sorted_comment_requests(requests, context, additions))
    
    # Return single stories first, then groups.
    yield from expel_stories(results, env, context)
    yield from expel_groups(results, env, context)


def _sorted_comment_requests(requests, context, additions):
    # Requests and pre-determined additions.
    results = itertools.chain(
        _parse_comment_requests(requests, context),
        additions
    )

    # Sort the reqults its position and only return the story item itself.
    results = sorted(results, key=lambda i: i[0])
    results = map(lambda i: i[-1], results)

    # Create a unique list out of the stories.
    if "nodistinct" not in context:
        results = _unique(results)

    # Return all results.
    yield from results


def _parse_comment_requests(requests, context):
    for site, queries in requests:
        # Ignore disabled sites.
        if site._disabled:
            continue

        # Do a little bit of logging.
        get_logger().info("Requests for '%s': %r" % (site.name, queries))
        # Begin processing the requests.
        for pos, query in queries:
            for comment in site.from_requests((query,), context):
                if comment is None:
                    continue
                yield (pos, query, comment)
