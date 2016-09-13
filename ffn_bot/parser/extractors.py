from .parser import parser, RequestParser
from ..fetchers import SITES


@RequestParser.register(100)
@parser()
def standard_requests(request):
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
        for story in site.from_request(request_list):
            if story is None:
                continue
            request.stories.append(story)

    return True

@RequestParser.register(100)
@parser(lambda request: 'direct' in request.markers)
def direct_links(request):
    for site in SITES:
        request.stories.append(site.extract_direct_links(request.content, request.markers))

    return True

