import sys
import argparse
import logging
import praw
from praw.objects import Submission

from ffn_bot.commentlist import CommentList
from ffn_bot.commentparser import formulate_reply, parse_context_markers
from ffn_bot.commentparser import get_direct_links
from ffn_bot.commentparser import StoryLimitExceeded
from ffn_bot import reddit_markdown
from ffn_bot import bot_tools

# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style

__author__ = 'tusing, MikroMan, StuxSoftware'

USER_AGENT = "Python:FanfictionComment:v1.1.2 (by tusing, StuxSoftware, and MikroMan)"
r = praw.Reddit(USER_AGENT)
DEFAULT_SUBREDDITS = ['HPFanfiction']
SUBREDDIT_LIST = set()
CHECKED_COMMENTS = None
FOOTER = "\n".join([
    r"**Bot v1.3.0 - 9/7/15** **|** \[[Usage][1]\] | \[[Changelog][2]\] | \[[Issues][3]\] | \[[GitHub][4]\]",
    r'[1]: https://github.com/tusing/reddit-ffn-bot/wiki/Usage       "How to use the bot"',
    r'[2]: https://github.com/tusing/reddit-ffn-bot/wiki/Changelog   "What changed until now"',
    r'[3]: https://github.com/tusing/reddit-ffn-bot/issues/          "Bugs? Suggestions? Enter them here!"',
    r'[4]: https://github.com/tusing/reddit-ffn-bot/                 "Fork me on GitHub"'
])
FOOTER += "\n\n^^^^^^^^^^^^^^^^^ffnbot!ignore"
FOOTER += "\n\n**Update Notes:** *Use* **ffnbot!delete** *to delete a comment!"
FOOTER +=  "Use* **ffnbot!refresh** *to refresh a bot replies!*"

# For testing purposes
DRY_RUN = False

# This is a experimental feature of the program
# Please use with caution
USE_STREAMS = False


def run_forever():
    sys.exit(_run_forever())


def _run_forever():
    """Run-Forever"""
    while True:
        try:
            main()
        # Exit on sys.exit and keyboard interrupts.
        except KeyboardInterrupt:
            raise
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

    if bot_parameters["experimental"]["streams"]:
        print("You are using the stream approach.")
        print("Please note that the application will not propely")
        print("restart on creashes due to limitations of the")
        print("Python threading interface.")
        USE_STREAMS = True

    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        print("Dry run enabled. No comment will be sent.")

    CHECKED_COMMENTS = CommentList(bot_parameters["comments"], DRY_RUN)

    level = getattr(logging, bot_parameters["verbosity"].upper())
    logging.getLogger().setLevel(level)


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
    if isinstance(obj, Submission):
        handle_submission(obj, markers)
    else:
        handle_comment(obj, markers)


def stream_handler(queue, iterator, handler):

    def _raise(exc):
        raise exc

    try:
        for post in iterator:
            print("Queueing Post:", post.id)
            queue.put_nowait((handler, post))
    except BaseException as e:
        # Send the actual exception to the main thread
        queue.put_nowait((_raise, e))


def post_receiver(queue):
    while True:
        handler, post = queue.get()
        handler(post)


def stream_strategy():
    from queue import Queue
    from threading import Thread
    from praw.helpers import submission_stream, comment_stream

    post_queue = Queue()

    threads = []
    threads.append(Thread(target=lambda: stream_handler(
        post_queue,
        comment_stream(
            r,
            "+".join(SUBREDDIT_LIST),
            limit=100,
            verbosity=0
        ),
        handle_comment
    )))
    threads.append(Thread(target=lambda: stream_handler(
        post_queue,
        submission_stream(
            r,
            "+".join(SUBREDDIT_LIST),
            limit=100,
            verbosity=0
        ),
        handle_submission
    )))

    for thread in threads:
        thread.daemon = True
        thread.start()

    while True:
        try:
            post_receiver(post_queue)
        except Exception as e:
            for thread in threads:
                if not thread.isAlive():
                    raise KeyboardInterrupt from e
            bot_tools.print_exception(e)


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

        bot_tools.pause(0, 30)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")
