import os
import sys
import logging
import praw
import platform
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
__version__ = "1.1.1"

# A nicer "standard" compliant user-agent for reddit.
# The first part is the required user agent data in their preferred
# format, then adding version information for the used software stack.
USER_AGENT = "%s (by /u/tusing)"%(
    # e.g. bot:FanFictionBot:1.1.1
    ":".join(["reply", "FanFiction", __version__]),
)

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
        handle
    ).run()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN, CHECKED_COMMENTS
    global DEBUG, FOOTER, SUBREDDIT_LIST
    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        print("Dry run enabled. No comment will be sent.")

    if CHECKED_COMMENTS is None or not DRY_RUN:
        CHECKED_COMMENTS = CommentList(bot_parameters["comments"], DRY_RUN)

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
    if (comment not in CHECKED_COMMENTS) or ("force" in extra_markers):
        logging.info("Found new comment: " + comment.id)
        markers = parse_context_markers(comment.body)
        markers |= extra_markers
        if "ignore" in markers:
            logging.debug("Comment forcefully ignored: " + comment.id)
            return

        if "parent" in markers:
            if comment.is_root:
                item = comment.submission
            else:
                item = r.get_info(thing_id=comment.parent_id)
            handle(item, {"directlinks", "submissionlink", "force"})

        make_reply(comment.body, comment.id, comment.reply, markers)


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

        # bot_tools.pause(1, 20)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")
