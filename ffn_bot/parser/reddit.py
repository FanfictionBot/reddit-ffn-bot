from .request import Request
import praw.objects as content_types


class RedditRequest(Request):
    """
    Base-Class for all reddit content type wrapper.
    """

    WRAPPED = {}

    @classmethod
    def wrap(cls, reddit, obj, markers=None):
        """
        Automatically wraps the correct object into the correct type.
        :param reddit:   The reddit instance.
        :param obj:      The object to be wrapped.
        :param markers:  The markers to attach
        :return: A RedditRequest-instance
        :raises: ValueError if the type is not supported.
        """
        for ocls in obj.__class__.mro():
            if ocls in cls.WRAPPED:
                return ocls(reddit, obj, markers)
        raise ValueError("Unsupported object type for reddit requests.")

    @classmethod
    def wrapper_for(cls, type, wrapper=None):
        """
        Registers a wrapper for reddit requests.

        :param type:      The type of the request.
        :param wrapper:   The wrapper.
        :return: A decorator or the class itself.
        """
        def _decorator(wrapper):
            cls.WRAPPED[type] = wrapper
            return wrapper

        if wrapper is not None:
            return _decorator(wrapper)
        return _decorator

    def __init__(self, reddit, request, markers=None):
        super(RedditRequest, self).__init__(request, markers)
        self.reddit = reddit


@RedditRequest.wrapper_for(content_types.Submission)
class Submission(RedditRequest):

    @property
    def content(self):
        return self.request.selftext


@RedditRequest.wrapper_for(content_types.Comment)
class Comment(RedditRequest):

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
