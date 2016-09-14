from .request import Request


class RedditRequest(Request):

    def __init__(self, reddit, request, markers=None):
        super(RedditRequest, self).__init__(request, markers)
        self.reddit = reddit


class Submission(RedditRequest):
    """
    Represents a praw.objects.Submission-object.
    """

    @property
    def content(self):
        return self.request.selftext


class Comment(RedditRequest):
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
