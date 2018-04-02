from .parser import parser, RequestParser
from ..fetchers import SITES


@RequestParser.register(100)
@parser()
def standard_requests(request):
    """
    This parser extracts the standard requests from the various sites.

    :param request:   The request.
    :return:          True.
    """
    for site in SITES:
        matches = site.regex.findall(request.content)

        # Split the request list using semicolons.
        request_list = []
        for item in matches:
            request_list.extend(item.split(";"))

        # Ensure we don't have empty request lists.
        if not request_list:
            continue

        # Add each story to the request.
        for story in site.from_requests(request_list, request.markers):
            if story is None:
                continue
            request.stories.append(story)

    return True


@RequestParser.register(100)
@parser(lambda request: 'directlinks' in request.markers)
def direct_links(request):
    """
    This parser extracts the direct links from the comments.

    This parser is only active on ffnbot!direct

    :param request: The request.
    :return: True.
    """
    for site in SITES:
        request.stories.extend(site.extract_direct_links(request.content, request.markers))
    return True


@RequestParser.register(200)
@parser(lambda request: request.markers.get('distinct', 'true').lower() == 'true')
def distinct_stories(request):
    """
    Makes the stories distinct while maintaining order.
    :param request:  The bot-request.
    :return: True
    """
    all_stories = set()
    deduplicated = []
    for story in request.stories:
        if story not in all_stories:
            all_stories.add(story)
            deduplicated.append(story)
    request.stories = deduplicated
    return True
