from praw import models as content_type

from .reddit import RedditRequest
from .parser import parser


@parser(lambda request: request.request.submission is not None)
def ignore_submission_messages(request):
    return False


@RedditRequest.wrapper_for(content_type.Message)
class Message(RedditRequest):

    def get_parsers(self):
        """
        Inject a ignore_submission_messages object into the beginning of the parser list so
        that submission messages are ignored.
        """
        yield ignore_submission_messages
        yield from super(Message, self).get_parsers()
