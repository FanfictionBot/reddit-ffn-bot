import os
import sys
import logging
import praw
from praw.objects import Submission, Comment

from ffn_bot.queues import QueueStrategy
from ffn_bot.commentlist import CommentList
from ffn_bot.commentparser import formulate_reply, parse_context_markers
from ffn_bot.commentparser import get_direct_links
from ffn_bot.commentparser import StoryLimitExceeded
from ffn_bot.cli import get_bot_parameters

from ffn_bot import bot_tools
from ffn_bot import cache
# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style

__author__ = 'tusing'
__authors__ = ['tusing', 'MikroMan', 'StuxSoftware']
__version__ = "1.3.0"

USER_AGENT = "Python:FanfictionComment:" + __version__ + " (by tusing, StuxSoftware, and MikroMan)"
r = praw.Reddit(USER_AGENT)
SUBREDDIT_LIST = set()
CHECKED_COMMENTS = None

FOOTER = ""

# For testing purposes
DRY_RUN = False

# Initiates the debug mode
# In stream mode it immediately jumps to
# queue newest object mode.
DEBUG = False


def run_forever():
    sys.exit(_run_forever())


def _run_forever():
    """Run-Forever"""
    while True:
        try:
            main()
        # Exit on sys.exit and keyboard interrupts.
        except KeyboardInterrupt as e:
            # Exit the program unclean.
            bot_tools.print_exception(e, level=logging.INFO)
            if CHECKED_COMMENTS is not None:
                CHECKED_COMMENTS.save()
            os._exit(0)
        except SystemExit as e:
            return e.code
        except:
            logging.error("MAIN: AN EXCEPTION HAS OCCURED!")
            bot_tools.print_exception()
            bot_tools.pause(1, 0)
        finally:
            if CHECKED_COMMENTS is not None:
                CHECKED_COMMENTS.save()


def main():
    """Basic main function."""
    # moved call for agruments to avoid double calling
    bot_parameters = get_bot_parameters()
    login_to_reddit(bot_parameters)
    init_global_flags(bot_parameters)

    QueueStrategy(
        r.get_subreddit("+".join(SUBREDDIT_LIST)),
        CHECKED_COMMENTS,
        handle,
        bot_parameters['limit']
    ).run()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN, CHECKED_COMMENTS
    global DEBUG, FOOTER, SUBREDDIT_LIST
    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        print("Dry run enabled. No comment will be sent.")

    if CHECKED_COMMENTS is None or not DRY_RUN:
        CHECKED_COMMENTS = CommentList(
            bot_parameters["comments"],
            DRY_RUN,
            bot_parameters["age"]
        )

    SUBREDDIT_LIST = bot_parameters['user_subreddits']

    level = getattr(logging, bot_parameters["verbosity"].upper())
    logging.getLogger().setLevel(level)

    if level == logging.DEBUG:
        DEBUG = True

    cache.default_cache = cache.RequestCache()

    with open(bot_parameters["footer"], "r") as f:
        FOOTER = f.read()
        FOOTER = FOOTER.format(version=__version__)
        print("==========================================")
        print(FOOTER)
        print("==========================================")

    if not DEBUG:
        logging.getLogger("requests").setLevel(logging.WARN)


def login_to_reddit(bot_parameters):
    """Performs the login for reddit."""
    print("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    print(Fore.GREEN, "Logged in.", Style.RESET_ALL)


def reply(post, message, reply_func=None):
    if DRY_RUN:
        logging.info("Not sending reply...")
        print(message)
        return

    logging.debug("Sending reply...")
    if reply_func is None:
        if isinstance(post, Comment):
            reply_func = post.reply
        elif isinstance(post, Submission):
            reply_func = post.add_comment

    reply_func(message + "\n" + FOOTER)
send_reply = reply


def get_parent(post, allow_submission=False):
    if not isinstance(post, Comment):
        raise ValueError("Comment required.")

    if post.is_root:
        if not allow_submission:
            return None

        return post.submission
    else:
        return r.get_info(thing_id=post.parent_id)


def _handle_submission(submission, markers=frozenset()):
    if (submission not in CHECKED_COMMENTS) or ("force" in markers):
        logging.info("Found new submission: " + submission.id)
        parse_submission_text(submission, markers)


def _handle_comment(comment, extra_markers=frozenset()):
    logging.debug("Handling comment: " + comment.id)
    if (comment not in CHECKED_COMMENTS) or ("force" in extra_markers):
        markers = parse_context_markers(comment.body)
        markers |= extra_markers
        if "ignore" in markers:
            # logging.info("Comment forcefully ignored: " + comment.id)
            return
        else:
            logging.info("Found new comment: " + comment.id)

        if "parent" in markers:
            item = get_parent(comment, allow_submission=True)
            handle(item, {"directlinks", "submissionlink", "force"})

        if "delete" in markers and (comment.id not in CHECKED_COMMENTS):
            logging.info("Delete requested by " + comment.id)
            if not comment.is_root:
                parent_comment = get_parent(comment)

                # Make sure we don't delete submissions.
                if not valid_comment(parent_comment):
                    logging.info("Cannot delete deleted comments :)")
                    return

                # Make sure the delete comment is actually authorized
                # We will inform the user that we ignored the comment
                # if we think he was not authorized to use the function.
                #
                # Make sure that the users know that they still have the
                # option of contacting a mod to remove the post.
                grand_parent = get_parent(parent_comment, True)
                if not valid_comment(grand_parent):
                    logging.info("Cannot verify authorization.")
                    send_reply(comment, "Cannot verify authorization.  \n\
Please contact a moderator to perform your request.")
                    return

                if grand_parent.author.name != comment.author.name:
                    logging.info("Comment not authorized.")
                    send_reply(comment, "Only the original comment author may request\
removing the bot reply.  \nIf you still think the comment should be\
removed contact a moderator or ask the comment author to remove\
the comment.")
                    return

                # Make sure we don't try to delete foreign posts.
                if parent_comment.author.name != r.user.name:
                    logging.error("Delete requested on non-bot comment.")
                    return

                # And only then, we will try to delete the comment.
                logging.info("Deleting comment " + parent_comment.id)
                parent_comment.delete()

        if "refresh" in markers and (comment not in CHECKED_COMMENTS):
            logging.info("(Refresh) Refresh requested by " + comment.id)

            # Get the full comment or submission
            comment_with_requests = get_full(get_parent(comment, True))
            logging.info("(Refresh) Refreshing on " + comment_with_requests.fullname)

            if comment_with_requests.author.name == r.user.name:
                logging.info(
                    "(Refresh) Refresh requested on a bot comment (" + comment_with_requests.id + ").")
                # Retrieve the requesting parent submission or comment
                comment_with_requests = get_full(
                    get_parent(comment_with_requests, True)
                )

                # If the requesting comment has been deleted, abort
                if not valid_comment(comment_with_requests):
                    logging.error("(Refresh) Parent of bot comment is invalid.")
                    return

                logging.info("Refresh request pushed to parent " + comment_with_requests.fullname)

            logging.info("(Refresh) Running refresh on:" + comment_with_requests.fullname)
            if isinstance(comment_with_requests, praw.objects.Comment):
                delete_list = comment_with_requests.replies
            elif isinstance(comment_with_requests, praw.objects.Submission):
                delete_list = comment_with_requests.comments
            else:
                logging.warning("Unsupported message type: " + comment_with_requests.fullname)
                return

            if delete_list:
                logging.info("(Refresh) Finding replies to delete.")
                for reply in delete_list:
                    if valid_comment(reply) and reply.author.name == r.user.name:
                        logging.error("(Refresh) Deleting bot comment " + reply.id)
                        reply.delete()
            else:
                logging.info(
                    "(Refresh) No bot replies have been deleted. Continuing...")
            handle(comment_with_requests, frozenset(["force"]))

        make_reply(comment.body, comment.id, comment.reply, markers)


def get_full(comment_id):
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
        logging.debug("Found comment resolving to None.")
        return False
    if comment.author is None:
        logging.debug("Found invalid comment " + comment.id)
        return False
    return True


def handle(obj, markers=frozenset()):
    try:
        if isinstance(obj, Submission):
            _handle_submission(obj, markers)
        else:
            _handle_comment(obj, markers)
    finally:
        CHECKED_COMMENTS.add(obj)


def parse_submission_text(submission, extra_markers=frozenset()):
    body = submission.selftext

    markers = parse_context_markers(body)
    markers |= extra_markers

    # Since the bot would start downloading the stories
    # here, we add the ignore option here
    if "ignore" in markers:
        return

    additions = []
    if "submissionlink" in markers:
        additions.extend(get_direct_links(submission.url, markers))

    make_reply(
        submission.selftext, submission.id, submission.add_comment,
        markers, additions)


def make_reply(body, id, reply_func, markers=None, additions=()):
    """Makes a reply for the given comment."""
    try:
        _reply = list(formulate_reply(body, markers, additions))
    except StoryLimitExceeded:
        # The user requested to many stories. (Which has never ever
        # happened).
        send_reply(
            None,
            ("You requested too many fics.\n"
                "\nWe allow a maximum of 30 stories"),
            reply_func
        )
        bot_tools.print_exception(level=logging.DEBUG)
        print("Too many fics...")
        bot_tools.pause(2, 0)
        return

    raw_reply = "".join(_reply)
    if len(raw_reply) > 10:
        print(
            "Writing reply to", id, "(", len(raw_reply), "characters in",
            len(_reply), "messages)")
        # Do not send the comment on dry-run.
        for part in _reply:
            reply(None, part, reply_func)
        bot_tools.pause(0, 30)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")
