import os
import sys
import logging
import praw
from praw.objects import Submission

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


def _handle_submission(submission, markers=frozenset()):
    if (submission not in CHECKED_COMMENTS) or ("force" in markers):
        logging.info("Found new submission: " + submission.id)
        parse_submission_text(submission, markers)


def _handle_comment(comment, extra_markers=frozenset()):
    logging.debug("Handling comment: " + comment.id)
    if (str(comment.id) not in CHECKED_COMMENTS
            ) or ("force" in extra_markers):

        markers = parse_context_markers(comment.body)
        markers |= extra_markers
        if "ignore" in markers:
            # logging.info("Comment forcefully ignored: " + comment.id)
            return
        else:
            logging.info("Found new comment: " + comment.id)

        if "parent" in markers:
            if comment.is_root:
                item = comment.submission
            else:
                item = r.get_info(thing_id=comment.parent_id)
            handle(item, {"directlinks", "submissionlink", "force"})

        if "delete" in markers and (comment.id not in CHECKED_COMMENTS):
            CHECKED_COMMENTS.add(str(comment.id))
            logging.info("Delete requested by " + comment.id)
            if not (comment.is_root):
                parent_comment = r.get_info(thing_id=comment.parent_id)
                if parent_comment.author is not None:
                    if (parent_comment.author.name == "FanfictionBot"):
                        logging.info("Deleting comment " + parent_comment.id)
                        parent_comment.delete()
                    else:
                        logging.error("Delete requested on non-bot comment!")
                else:
                    logging.error("Delete requested on null comment.")
            else:
                logging.error("Delete requested by invalid comment!")

        if "refresh" in markers and (str(comment.id) not in CHECKED_COMMENTS):
            CHECKED_COMMENTS.add(str(comment.id))
            logging.info("(Refresh) Refresh requested by " + comment.id)

            # Get the full comment or submission
            comment_with_requests = get_full(comment.parent_id)
            logging.info("(Refresh) Refreshing on " + type(
                comment_with_requests).__name__ + " with id " + comment_with_requests.id)

            # TODO: Make it so FanfictionBot does not have to be hardcoded
            # If ffnbot!refresh is called on an actual bot reply, then go up
            # one level to find the requesting comment
            if comment_with_requests.author.name == "FanfictionBot":
                logging.info(
                    "(Refresh) Refresh requested on a bot comment (" + comment_with_requests.id + ").")
                # Retrieve the requesting parent submission or comment
                comment_with_requests = get_full(
                    comment_with_requests.parent_id)

                # If the requesting comment has been deleted, abort
                if not valid_comment(comment_with_requests):
                    logging.error(
                        "(Refresh) Parent of bot comment is invalid.")
                    return

                logging.info(
                    "          Refresh request being pushed to parent " + comment_with_requests.id)

            if isinstance(comment_with_requests, praw.objects.Comment):
                logging.info(
                    "(Refresh) Running refresh on COMMENT " + str(comment_with_requests.id))
                logging.info("(Refresh) Appending replies to deletion check list: " +
                             ", ".join(str(c.id) for c in comment_with_requests.replies))
                delete_list = comment_with_requests.replies

            elif isinstance(comment_with_requests, praw.objects.Submission):
                logging.info(
                    "(Refresh) Running refresh on SUBMISSION " + str(comment_with_requests.id))

                unfiltered_delete_list = comment_with_requests.comments
                delete_list = []
                for comment in unfiltered_delete_list:
                    if comment.author is not None:
                        if (comment.author.name == "FanfictionBot"):
                            delete_list.append(comment)
                            print("(Refresh) Found root-level bot comment " + comment.id)
            else:
                logging.error("(Refresh) Can't refresh " + comment_with_requests.type(
                ).__name__ + " with ID " + comment_with_requests.id)
                bot_tools.pause(5, 0)
                return

            if delete_list is not None:
                logging.info("(Refresh) Finding replies to delete.")
                for reply in delete_list:
                    if valid_comment(reply):
                        if (reply.author.name == "FanfictionBot"):
                            logging.error(
                                "(Refresh) Deleting bot comment " + reply.id)
                            reply.delete()
            else:
                logging.info(
                    "(Refresh) No bot replies have been made. Continuing...")
            CHECKED_COMMENTS.add(str(comment.id))

            if isinstance(comment_with_requests, praw.objects.Comment):
                logging.info(
                    "(Refresh) Re-handling comment " + comment_with_requests.id)
                handle_comment(comment_with_requests, frozenset(["force"]))
            elif isinstance(comment_with_requests, praw.objects.Submission):
                logging.info(
                    "(Refresh) Re-handling submission " + comment_with_requests.id)
                handle_submission(comment_with_requests, frozenset(["force"]))
            return

        try:
            make_reply(comment.body, comment.id, comment.reply, markers)
        finally:
            CHECKED_COMMENTS.add(str(comment.id))


def get_full(comment_id):
    """
    Will return a full comment or submission.
    Very heavy on time.
    """
    requested_comment = r.get_info(thing_id=comment_id)
    if isinstance(requested_comment, praw.objects.Comment):
        # PRAW doesn't return replies in a comment object retrieved with
        # get_info; we must do this:
        requested_comment = r.get_submission(
            requested_comment.permalink).comments[0]
    elif isinstance(requested_comment, praw.objects.Submission):
        requested_comment = r.get_submission(requested_comment.permalink)
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
    if comment.author is None:
        logging.error("Found invalid comment " + comment.id)
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
        reply = list(formulate_reply(body, markers, additions))
    except StoryLimitExceeded:
        if not DRY_RUN:
            reply_func("You requested too many fics.\n"
                       "\nWe allow a maximum of 30 stories")
        bot_tools.print_exception(level=logging.DEBUG)
        print("Too many fics...")
        bot_tools.pause(2, 0)
        return

    raw_reply = "".join(reply)
    if len(raw_reply) > 10:
        print(
            "Writing reply to", id, "(", len(raw_reply), "characters in",
            len(reply), "messages)")
        # Do not send the comment.
        if not DRY_RUN:
            for part in reply:
                reply_func(part + FOOTER)
        bot_tools.pause(0, 30)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")
