import praw.objects
import logging


def get_full(r, comment_id):
    """
    Will return a full comment or submission.
    """
    if isinstance(comment_id, str):
        requested_comment = r.get_info(thing_id=comment_id)
    else:
        requested_comment = comment_id

    if isinstance(requested_comment, praw.objects.Comment):
        # To make this faster, we check if we already get a list of
        # a replies before we go off to reddit refreshing this comment
        # object.
        if not requested_comment.replies:
            requested_comment.refresh()
    elif isinstance(requested_comment, praw.objects.Submission):
        requested_comment.refresh()
        requested_comment.replace_more_comments(limit=None, threshold=0)
    else:
        logging.error(
            "(URGENT) WAS NOT ABLE TO DETERMINE COMMENT VS SUBMISSION!")
        requested_comment = r.get_submission(requested_comment.permalink)
    return requested_comment


def valid_comment(comment):
    """
    Checks if valid comment.
    """
    if comment is None:
        logging.info("Found comment resolving to None.")
        return False

    if comment.author is None:
        logging.info("Found invalid comment " + comment.id)
        return False
    return True


def get_parent(r, post, allow_submission=False):
    if not isinstance(post, praw.objects.Comment):
        raise ValueError("Comment required.")

    if post.is_root:
        if not allow_submission:
            return None

        return post.submission
    else:
        return r.get_info(thing_id=post.parent_id)
