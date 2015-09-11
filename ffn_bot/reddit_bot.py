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
from ffn_bot.config import get_bot_parameters, get_settings
from ffn_bot.moderation import ModerativeCommands
from ffn_bot.auth import login_to_reddit

from ffn_bot import bot_tools
from ffn_bot import cache
# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style
from ffn_bot.bot_tools import get_parent, get_full, valid_comment

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

MOD_COMMANDS = None

def run_forever():
    sys.exit(_run_forever())


def _run_forever():
    """Run-Forever"""
    while True:
        try:
            return main()
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
    if not login_to_reddit(r, get_settings()):
        logging.critical("Failed to login. Stopping bot.")
        return 1

    init_global_flags(bot_parameters)

    QueueStrategy(
        r.get_subreddit("+".join(SUBREDDIT_LIST)),
        CHECKED_COMMENTS,
        handle,
        bot_parameters['limit']
    ).run()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN, CHECKED_COMMENTS
    global DEBUG, FOOTER, SUBREDDIT_LIST, MOD_COMMANDS
    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        logging.warning("Dry run enabled. No comment will be sent.")

    if CHECKED_COMMENTS is None or not DRY_RUN:
        CHECKED_COMMENTS = CommentList(
            bot_parameters["comments"],
            DRY_RUN,
            bot_parameters["age"]
        )

    SUBREDDIT_LIST = bot_parameters['user_subreddits']
    cache.default_cache = cache.RequestCache()

    with open(bot_parameters["footer"], "r") as f:
        FOOTER = f.read()
        FOOTER = FOOTER.format(version=__version__)
        logging.info("==========================================")
        for line in FOOTER.split("\n"):
            logging.info(line)
        logging.info("==========================================")

    MOD_COMMANDS = ModerativeCommands(r, CHECKED_COMMENTS, reply, handle)


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

        if MOD_COMMANDS.handle_moderation(comment, markers):
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
