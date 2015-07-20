import os
import sys
import argparse
import logging
import praw
from praw.objects import Submission

from ffn_bot.commentlist import CommentList
from ffn_bot.commentparser import formulate_reply, parse_context_markers
from ffn_bot.commentparser import get_direct_links
from ffn_bot.commentparser import StoryLimitExceeded
from ffn_bot.streams import full_reddit_stream

from ffn_bot import reddit_markdown
from ffn_bot import bot_tools

# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style

__author__ = 'tusing, MikroMan, StuxSoftware'

USER_AGENT = "Python:FanfictionComment:v0.5 (by tusing, StuxSoftware, and MikroMan)"
r = praw.Reddit(USER_AGENT)
DEFAULT_SUBREDDITS = ['HPFanfiction', 'fanfiction', 'HPMOR']
SUBREDDIT_LIST = set()
CHECKED_COMMENTS = None

FOOTER = "\n\nRead usage tips and tricks  [**here**](https://github.com/tusing/reddit-ffn-bot/blob/master/README.md).\n\n" + "\n\nSupporting fanfiction.net (*linkffn*), AO3 (fixed!) (*linkao3*), HPFanficArchive (*linkffa*), FictionPress (*linkfp*), AdultFanFiction (linkaff) (story ID only)\n\n"

exponentiated = [
    "**New Features 7/19/15:** Download EPUB links for FFNet, FP, and AO3! ffnbot!parent call added!",
    "Parse multiple fics in a single call with;semicolons;like;this!",
    "*Add the following tags to any comment:* ",
    "- *ffnbot!parent*: create a reply for all links in a parent comment",
    "- *ffnbot!directlinks*: auto parse fanfiction site links without having to call the bot"
]

for string in exponentiated:
    FOOTER += reddit_markdown.exponentiate(string) + "\n\n"

FOOTER += "^^^^^^^^^^^^^^^^^ffnbot!ignore"

# For testing purposes
DRY_RUN = False

# This is a experimental feature of the program
# Please use with caution
USE_STREAMS = False

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
    load_subreddits(bot_parameters)
    init_global_flags(bot_parameters)

    if USE_STREAMS:
        print("========================================")
        print("Stream Based, Will not gracefully restart.")
        stream_strategy()
        sys.exit()

    while True:
        single_pass()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN, CHECKED_COMMENTS, USE_STREAMS
    global DEBUG

    if bot_parameters["experimental"]["streams"]:
        print("You are using the stream approach.")
        print("Please note that the application will not propely")
        print("restart on creashes due to limitations of the")
        print("Python threading interface.")
        USE_STREAMS = True

    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        print("Dry run enabled. No comment will be sent.")

    if CHECKED_COMMENTS is None or not DRY_RUN:
        CHECKED_COMMENTS = CommentList(bot_parameters["comments"], DRY_RUN)

    level = getattr(logging, bot_parameters["verbosity"].upper())
    logging.getLogger().setLevel(level)

    if level == logging.DEBUG:
        DEBUG = True

def get_bot_parameters():
    """Parse the command-line arguments."""
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user',
                        help='define Reddit login username')
    parser.add_argument(
        '-p', '--password',
        help='define Reddit login password')

    parser.add_argument(
        '-s', '--subreddits',
        help='define target subreddits; seperate with commas')

    parser.add_argument(
        '-d', '--default',
        action='store_true',
        help='add default subreddits, can be in addition to -s')

    parser.add_argument(
        '-c', '--comments',
        help="Filename where comments are stored",
        default="CHECKED_COMMENTS.txt")

    parser.add_argument(
        '-l', '--dry',
        action='store_true',
        help="do not send comments.")

    parser.add_argument(
        "--streams",
        action="store_true",
        help="Highly experimental feature. Handle posts as they come")

    parser.add_argument(
        "-v", "--verbosity",
        default="INFO",
        help="The default log level. Using python level states.")

    args = parser.parse_args()

    return {
        'user': args.user,
        'password': args.password,
        'user_subreddits': args.subreddits,
        'default': args.default,
        'dry': args.dry,
        'comments': args.comments,
        'verbosity': args.verbosity,
        # Switches for experimental features
        'experimental': {
            "streams": args.streams
        }
    }


def login_to_reddit(bot_parameters):
    """Performs the login for reddit."""
    print("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    print(Fore.GREEN, "Logged in.", Style.RESET_ALL)


def load_subreddits(bot_parameters):
    """Loads the subreddits this bot operates on."""
    global SUBREDDIT_LIST
    print("Loading subreddits...")

    if bot_parameters['default'] is True:
        print("Adding default subreddits: ", DEFAULT_SUBREDDITS)
        for subreddit in DEFAULT_SUBREDDITS:
            SUBREDDIT_LIST.add(subreddit)

    if bot_parameters['user_subreddits'] is not None:
        user_subreddits = bot_parameters['user_subreddits'].split(',')
        print("Adding user subreddits: ", user_subreddits)
        for subreddit in user_subreddits:
            SUBREDDIT_LIST.add(subreddit)

    if len(SUBREDDIT_LIST) == 0:
        print("No subreddit specified. Adding test subreddit.")
        SUBREDDIT_LIST.add('tusingtestfield')
    print("LOADED SUBREDDITS: ", SUBREDDIT_LIST)


def handle_submission(submission, markers=frozenset()):
    if not is_submission_checked(submission) or ("force" in markers):
        logging.info("Found new submission: " + submission.id)
        try:
            parse_submission_text(submission, markers)
        finally:
            check_submission(submission)


def handle_comment(comment, extra_markers=frozenset()):
    logging.debug("Handling comment: " + comment.id)
    if (str(comment.id) not in CHECKED_COMMENTS
       ) or ("force" in extra_markers):

        logging.info("Found new comment: " + comment.id)
        markers = parse_context_markers(comment.body)
        markers |= extra_markers
        if "ignore" in markers:
            logging.info("Comment forcefully ignored: " + comment.id)
            return

        if "parent" in markers:
            if comment.is_root:
                item = comment.submission
            else:
                item = r.get_info(thing_id=comment.parent_id)
            handle(item, {"directlinks", "submissionlink", "force"})

        try:
            make_reply(comment.body, comment.id, comment.reply, markers)
        finally:
            CHECKED_COMMENTS.add(str(comment.id))


def handle(obj, markers=frozenset()):
    if isinstance(obj, Submission):
        handle_submission(obj, markers)
    else:
        handle_comment(obj, markers)


def stream_strategy():
    iterator = full_reddit_stream(
        r,
        "+".join(SUBREDDIT_LIST),
        limit=1 if DEBUG else 100,
        verbosity=0
    )

    try:
        for post in iterator:
            handle(post)

    finally:
        # Make sure the iterator will stop
        # its internal executor sometime in the future.
        iterator.close()


def single_pass():
    try:
        # We actually use a multireddit to acieve our goal
        # of watching multiple reddits.
        subreddit = r.get_subreddit("+".join(SUBREDDIT_LIST))

        logging.info("Parsing new submissions.")
        for submission in subreddit.get_new(limit=50):
            handle_submission(submission)

        logging.info("Parsing new comments.")
        for comment in subreddit.get_comments(limit=100):
            handle_comment(comment)
    except Exception:
        bot_tools.print_exception()
    bot_tools.pause(1, 0)


def check_submission(submission):
    """Mark the submission as checked."""
    global CHECKED_COMMENTS
    CHECKED_COMMENTS.add("SUBMISSION_" + str(submission.id))


def is_submission_checked(submission):
    """Check if the submission was checked."""
    global CHECKED_COMMENTS
    return "SUBMISSION_" + str(submission.id) in CHECKED_COMMENTS


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

        bot_tools.pause(1, 20)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")
