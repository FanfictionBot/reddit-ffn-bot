import os
import sys
import logging
import praw
from praw.objects import Submission, Comment
from praw.handlers import MultiprocessHandler

from ffn_bot import cache
from ffn_bot import bot_tools

from ffn_bot.stats import FicCounter
from ffn_bot.commentparser import get_direct_links
from ffn_bot.commentparser import StoryLimitExceeded, GroupLimitExceeded
from ffn_bot.commentparser import formulate_reply, parse_context_markers

from ffn_bot.reddit.auth import login_to_reddit
from ffn_bot.reddit.queues import QueueStrategy
from ffn_bot.reddit.settings import get_bot_parameters, get_settings
from ffn_bot.reddit.moderation import ModerativeCommands
from ffn_bot.reddit.commentlist import CommentList
from ffn_bot.reddit.reddit_environment import RedditBotEnvironment

__author__ = 'tusing'
__authors__ = ['tusing', 'MikroMan', 'StuxSoftware']
__version__ = "1.4.0"

USER_AGENT = "Python:FanfictionComment:" + __version__ + \
    " (by tusing, StuxSoftware, and MikroMan)"

# Start PRAW Multiprocess by running "praw-multiprocess"
handler = MultiprocessHandler()
r = praw.Reddit(USER_AGENT, handler=handler)
r._use_oauth = False  # A temporary band-aid.

SUBREDDIT_LIST = set()
CHECKED_COMMENTS = None

FOOTER = ""

# For testing purposes
DRY_RUN = False

# Initiates the debug mode
# In stream mode it immediately jumps to
# queue newest object mode.
DEBUG = False

TRACKER = None
ENVIRONMENT = None
MOD_COMMANDS = None


def save_things():
    if CHECKED_COMMENTS is not None:
        CHECKED_COMMENTS.save()
    if TRACKER is not None:
        TRACKER.save()


def run_forever(argv):
    sys.exit(_run_forever(argv))


def _run_forever(argv):
    """Run-Forever"""
    while True:
        try:
            return main(argv)
        # Exit on sys.exit and keyboard interrupts.
        except KeyboardInterrupt as e:
            # Exit the program unclean.
            bot_tools.print_exception(e, level=logging.debug)
            save_things()
            os._exit(0)
        except SystemExit as e:
            return e.code
        except:
            logging.error("MAIN: AN EXCEPTION HAS OCCURED!")
            bot_tools.print_exception()
            bot_tools.pause(1, 0)
        finally:
            save_things()


def main(argv):
    """Basic main function."""
    # moved call for agruments to avoid double calling
    bot_parameters = get_bot_parameters(argv)
    if not login_to_reddit(r, get_settings()["bot"]["credentials"]):
        logging.critical("Failed to login. Stopping bot.")
        return 1

    init_global_flags(bot_parameters)

    QueueStrategy(
        r,
        r.get_subreddit("+".join(SUBREDDIT_LIST)),
        CHECKED_COMMENTS,
        handle,
        bot_parameters['limit']
    ).run()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN, CHECKED_COMMENTS
    global DEBUG, FOOTER, SUBREDDIT_LIST, MOD_COMMANDS
    global ENVIRONMENT, TRACKER
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
        logging.debug("==========================================")
        for line in FOOTER.split("\n"):
            logging.debug(line)
        logging.debug("==========================================")

    MOD_COMMANDS = ModerativeCommands(r, CHECKED_COMMENTS, reply, handle)

    settings = get_settings()
    tracker_settings = settings["bot"].get("tracker", {
        "filename": "tracker.json", "autosave_interval": 100
    })

    TRACKER = FicCounter(**tracker_settings)
    ENVIRONMENT = RedditBotEnvironment(TRACKER)


def reply(post, message, reply_func=None):
    if DRY_RUN:
        logging.info("Not sending reply...")
        logging.info("\n" + message)
        return

    logging.info("Sending reply...")
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
    logging.info("Handling comment " + comment.id)

    if (comment not in CHECKED_COMMENTS) or ("force" in extra_markers):
        markers = parse_context_markers(comment.body)
        markers |= extra_markers
        if "ignore" in markers:
            return
        else:
            logging.info("Found new comment: " + comment.id)
        r.use_oauth = False
        submission = comment.submission
        submission.refresh()
        submission_markers = parse_context_markers(submission.selftext)
        if "disable" in submission_markers:
            return

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
    logging.debug("Attempting a reply to: ")
    logging.debug(body)

    try:
        _reply = list(formulate_reply(body, ENVIRONMENT, markers, additions))
    except StoryLimitExceeded:
        # The user requested to many stories. (Which has never ever
        # happened).
        send_reply(
            None,
            (
                "*You requested too many fics.*\n\n"
                "We allow a maximum of 30 stories to prevet abuse.\n\n"
                "Please remove some requests and use **ffnbot\\!refresh** "
                "to retry parsing."
            ),
            reply_func
        )
        logging.info("User requested too many fics...")
        bot_tools.pause(2, 0)
        return
    except GroupLimitExceeded:
        send_reply(
            None,
            (
                "*You requested too many groupings.*\n\n"
                "We allow up to five groups to ensure the bot doesn't "
                "disrupt the current conversation.\n\n"
                "Please remove some requests and use **ffnbot\\!refresh** "
                "to retry parsing."
            ),
            reply_func
        )
        logging.info("User requests too many groups...")
        bot_tools.pause(4, 0)
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
        logging.info("No reply conditions met for " + id)
